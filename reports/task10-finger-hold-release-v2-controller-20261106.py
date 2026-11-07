"""Runtime fixed-joint adapter. Never writes object poses or velocities."""
from dataclasses import asdict
from pathlib import Path
import json,math,re
import numpy as np
from scipy.spatial.transform import Rotation
from grasp_gate import GraspGate,GateConfig,Sample

def relative(palm,obj):
    rp=Rotation.from_quat(np.roll(np.asarray(palm[3:7]),-1));ro=Rotation.from_quat(np.roll(np.asarray(obj[3:7]),-1))
    return rp.inv().apply(np.asarray(obj[:3])-palm[:3]),np.roll((rp.inv()*ro).as_quat(),1)

class PhysXAttachment:
    def __init__(self,scene,output,config=None):
        from pxr import UsdPhysics
        self.scene=scene;self.stage=scene.sim.stage;self.config=config or GateConfig();self.frame_probe_path=Path(output)/'JOINT_FRAME_PROBE.jsonl'
        from native_attachment_precision import NativeAttachmentPrecision
        self.precision=NativeAttachmentPrecision(scene,output)
        self.precision.enable=lambda i,key:None
        self.precision.disable=lambda i:None
        self.keys=list(scene.contacts[0].env.object_ids)
        self.gates=[GraspGate(self.config) for _ in range(scene.count)]
        self.active=[None]*scene.count;self.events=[];self.raw_command=None
        self.rest_z=np.asarray(scene.initial)[:,:,2].copy();self.max_error_m=0.;self.max_error_rad=0.;self.previous_raw_command=None;self.gap_digits=[None]*scene.count;self.last_samples=[None]*scene.count
        self.stream=(Path(output)/'ATTACHMENT_EVENTS.jsonl').open('x')
        self.sample_stream=(Path(output)/'GRASP_SAMPLES.jsonl').open('x')
        self.hand_paths=[]
        for i,view in enumerate(scene.contacts):
            paths=[p for p in view.actors if '/Robot/hand2_' in p or p.endswith('/Robot/arm2_link7')]
            palm=f'/World/envs/env_{i}/Robot/hand2_link_base'
            assert palm in paths and self.stage.GetPrimAtPath(palm).HasAPI(UsdPhysics.RigidBodyAPI),'no_native_palm_body'
            self.hand_paths.append(paths)
        self.save_contract(output)
    def save_contract(self,output):
        p=Path(output)/'ATTACHMENT_CONTRACT.json'
        p.write_text(json.dumps(dict(mode='stable30_native32_finger_hold_v2_measured_open_release',config=asdict(self.config),
            object_pose_writes=False,object_velocity_writes=False,visual_mesh_edits=False,
            numerical_variant="native_solver_unchanged_32",
            filtered_bodies=[],finger_collisions_retained=True,hold_fingers_at_measured_grasp=True,policy_joint_targets_modified=True,arm_policy_targets_modified=False,
            release='absolute_open_target_vs_measured_held_grasp30mrad_before_next_step_OR_measured_finger_gap_increase_same_tick',
            finger_gap_measure='world_link_center_distance_thumb1_3_to_fixed_contacting_opponent_digit2',
            pairwise_relative_window_diameter=True,
            task_labels_or_oracle_as_input=False),indent=2)+'\n')
    def before_step(self):
        q=self.scene.command[:,self.scene.ids].detach().cpu().numpy().copy()
        self.raw_command=q.copy()
        for i,a in enumerate(self.active):
            if a is None:continue
            now=float(q[i,8:10].mean())
            prior=float(self.previous_raw_command[i,8:10].mean()) if self.previous_raw_command is not None else a['commanded_open_mean']
            if now>=self.config.command_open_mean_rad:
                self._release(i,'policy_opening_command_before_step')
            elif now>float(a['finger_q'][1:3].mean())+self.config.command_increase_epsilon_rad:
                self._release(i,'measured_grasp_opening_30mrad_before_step')
            elif float(q[i,7])<float(a['finger_q'][0])-self.config.command_increase_epsilon_rad:
                self._release(i,'measured_thumb_opening_30mrad_before_step')
        # No policy joint target is held, replaced, filtered or rewritten.
        self.previous_raw_command=q.copy()
        # Preserve the raw policy command for interpolation and opening detection.
        # Only the actual PhysX finger target is held while the fixed joint is active.
        delivered=self.scene.command.clone()
        for i,a in enumerate(self.active):
            if a is not None:delivered[i,self.scene.hand_ids]=delivered.new_tensor(a['finger_q'])
        self.scene.robot.set_joint_position_target(delivered)

    def _finger_gap(self,i,actors,digits):
        if self.active[i] is not None:digit=self.active[i]['gap_digit']
        else:
            opposing=sorted(d for d in digits if d!=1)
            assert opposing,'missing_opposing_digit_for_gap'
            digit=opposing[0];self.gap_digits[i]=digit
        thumb=f'/World/envs/env_{i}/Robot/hand2_link_1_3'
        other=f'/World/envs/env_{i}/Robot/hand2_link_{digit}_2'
        assert thumb in actors and other in actors,'finger_gap_actor_missing'
        return float(np.linalg.norm(np.asarray(actors[thumb][:3])-np.asarray(actors[other][:3])))
    def after_step(self,contacts_by_env=None):
        assert self.raw_command is not None,'before_step_not_called'
        q=self.scene.qpos();rows=contacts_by_env or [v.sample() for v in self.scene.contacts]
        poses=self.scene.poses()
        for i,(gate,contacts) in enumerate(zip(self.gates,rows)):
            actors=self.scene.contacts[i].actor_poses()
            # Tensor actor_poses use xyzw, canonical scene object states use wxyz.
            palm_path=f'/World/envs/env_{i}/Robot/hand2_link_base'
            palm=np.asarray(actors[palm_path],float);palm[3:]=np.roll(palm[3:],1)
            hand_by_key={k:[r for r in contacts if r['object']==k and '/Robot/hand2_' in r['actor'] and r['contact_count']>0] for k in self.keys}
            support_by_key={k:any(r['object']==k and '/Robot/' not in r['actor'] and r['contact_count']>0 for r in contacts) for k in self.keys}
            for j,k in enumerate(self.keys):
                if not hand_by_key[k] and support_by_key[k] and gate.attached!=k:self.rest_z[i,j]=poses[i,j,2]
            key=gate.attached
            if key is None:
                candidates=[]
                for j,k in enumerate(self.keys):
                    digits={int(m.group(1)) for r in hand_by_key[k] if (m:=re.search(r'/hand2_link_(\d)_',r['actor']))}
                    if 1 in digits and any(d!=1 for d in digits):candidates.append((k,j))
                # Ambiguous simultaneous two-object grasp must not create a lucky attachment.
                key=candidates[0][0] if len(candidates)==1 else ''
            if key:
                j=self.keys.index(key);obj=poses[i,j];pos,quat=relative(palm,obj)
                digits={int(m.group(1)) for r in hand_by_key[key] if (m:=re.search(r'/hand2_link_(\d)_',r['actor']))}
                up=float(Rotation.from_quat(np.roll(obj[3:],-1)).apply([0,0,1])[2])
                s=Sample(self.scene.tick_count,key,float(obj[2]-self.rest_z[i,j]),1 in digits,any(d!=1 for d in digits),support_by_key[key],tuple(pos),tuple(quat),up,float(q[i,8:10].mean()),float(self.raw_command[i,8:10].mean()),self._finger_gap(i,actors,digits))
            else:s=Sample(self.scene.tick_count,'',0.,False,False,False,(0.,0.,0.),(1.,0.,0.,0.),1.,float(q[i,8:10].mean()),float(self.raw_command[i,8:10].mean()))
            self.last_samples[i]=s
            self.sample_stream.write(json.dumps(dict(environment=i,**asdict(s)),allow_nan=False)+'\n')
            action=gate.update(s)
            if action=='attach':self._attach(i,key,palm_path,s,q[i,7:13],contacts)
            elif action=='release':self._release(i,gate.last_release_reason,s)
            elif self.active[i] is not None:
                a=self.active[i];dp=float(np.linalg.norm(np.asarray(s.relative_position)-a['relative_position']))
                dq=2*math.acos(min(1.,abs(float(np.dot(s.relative_quaternion_wxyz,a['relative_quaternion_wxyz'])))))
                self.max_error_m=max(self.max_error_m,dp);self.max_error_rad=max(self.max_error_rad,dq)
                if self.scene.tick_count>a['tick']+8 and (dp>.02 or dq>.2):raise RuntimeError('fixed_constraint_not_holding:'+str((i,dp,dq)))
        return rows
    def _event(self,x):
        self.events.append(x);self.stream.write(json.dumps(x,allow_nan=False)+'\n');self.stream.flush()
    def _attach(self,i,key,palm,s,finger_q,contacts):
        from pxr import UsdPhysics,Gf,Sdf
        assert self.active[i] is None
        body=f'/World/envs/env_{i}/Beaker{key}/base';prim=self.stage.GetPrimAtPath(body)
        try:
            dc=self.precision.control
            def native_pose(path):
                handle=dc.get_rigid_body(path)
                if handle==self.precision.invalid:return None
                t=dc.get_rigid_body_pose(handle)
                return [t.p.x,t.p.y,t.p.z,t.r.w,t.r.x,t.r.y,t.r.z]
            npalm=native_pose(palm);nobj=native_pose(body)
            actual_pos,actual_quat=relative(np.asarray(npalm),np.asarray(nobj)) if npalm is not None and nobj is not None else (None,None)
            record={'tick':s.tick,'key':key,'native_palm':npalm,'native_object':nobj,
                    'authored_relative_position':list(s.relative_position),'authored_relative_quaternion_wxyz':list(s.relative_quaternion_wxyz),
                    'native_relative_position':actual_pos.tolist() if actual_pos is not None else None,
                    'native_relative_quaternion_wxyz':actual_quat.tolist() if actual_quat is not None else None,
                    'relative_position_error_m':float(np.linalg.norm(actual_pos-np.asarray(s.relative_position))) if actual_pos is not None else None}
            with self.frame_probe_path.open('a') as f:f.write(json.dumps(record,allow_nan=False)+'\n')
        except Exception as error:
            with self.frame_probe_path.open('a') as f:f.write(json.dumps({'tick':s.tick,'probe_error':type(error).__name__})+'\n')

        # Preserve native collision API and pair relationships byte-for-byte.
        path=f'/World/envs/env_{i}/GraspAttachment/hand2_fixed'
        assert not self.stage.GetPrimAtPath(path),'attachment_joint_path_already_exists'
        joint=UsdPhysics.FixedJoint.Define(self.stage,path)
        joint.CreateJointEnabledAttr(False);joint.CreateExcludeFromArticulationAttr(True)
        joint.CreateBody0Rel().SetTargets([Sdf.Path(palm)]);joint.CreateBody1Rel().SetTargets([Sdf.Path(body)])
        joint.CreateLocalPos0Attr().Set(Gf.Vec3f(*s.relative_position));joint.CreateLocalRot0Attr().Set(Gf.Quatf(s.relative_quaternion_wxyz[0],Gf.Vec3f(*s.relative_quaternion_wxyz[1:])))
        joint.CreateLocalPos1Attr().Set(Gf.Vec3f(0,0,0));joint.CreateLocalRot1Attr().Set(Gf.Quatf(1,Gf.Vec3f(0,0,0)))
        joint.CreateCollisionEnabledAttr(False);joint.CreateJointEnabledAttr(True)
        self.active[i]=dict(key=key,joint=path,body=body,finger_q=finger_q.copy(),
            tick=s.tick,gap_digit=self.gap_digits[i],commanded_open_mean=s.commanded_finger_mean,raw_thumb_command=float(self.raw_command[i,7]),relative_position=np.asarray(s.relative_position),relative_quaternion_wxyz=np.asarray(s.relative_quaternion_wxyz))
        self.precision.enable(i,key)
        self._event(dict(event='attach',environment=i,key=key,tick=s.tick,duration_ticks=0,body0=palm,body1=body,joint_path=path,measured_sample=asdict(s),held_finger_targets_rad=finger_q.tolist(),raw_thumb_command_at_latch=float(self.raw_command[i,7]),measured_thumb_release_reference=float(finger_q[0]),measured_opposing_release_reference=float(finger_q[1:3].mean()),
            opposing_contact_rows=[r for r in contacts if r['object']==key and '/hand2_' in r['actor']],joint_type='PhysicsFixedJoint',exclude_from_articulation=True))
    def _release(self,i,reason,s=None):
        from pxr import UsdPhysics
        a=self.active[i]
        if a is None:return
        self.stage.RemovePrim(a['joint'])
        self._event(dict(event='release',environment=i,key=a['key'],tick=self.scene.tick_count,reason=reason,
            measured_sample=asdict(s) if s else None,raw_hand_command_rad=self.raw_command[i,7:13].tolist(),held_finger_targets_rad=a['finger_q'].tolist(),opening_reference='measured_grasp',attached_tick=a['tick'],duration_ticks=self.scene.tick_count-a['tick'],duration_s=(self.scene.tick_count-a['tick'])/120,native_collision_api_and_pairs_unchanged=True,joint_removed=not bool(self.stage.GetPrimAtPath(a['joint']))))
        self.active[i]=None;self.gap_digits[i]=None
        self.gates[i].release_now(self.scene.tick_count,reason)
        self.precision.disable(i)
    def attached_keys(self,i):return {self.active[i]['key']} if self.active[i] else set()
    def close(self):
        for i in range(len(self.active)):self._release(i,'owned_cleanup')
        self.precision.close()
        self.stream.close();self.sample_stream.close()
    def summary(self):return dict(activations=sum(e['event']=='attach' for e in self.events),releases=sum(e['event']=='release' and e['reason']!='owned_cleanup' for e in self.events),
        maximum_relative_translation_error_m=self.max_error_m,maximum_relative_rotation_error_rad=self.max_error_rad,active_keys=[list(self.attached_keys(i)) for i in range(len(self.active))])
