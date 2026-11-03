"""Independent closed-episode T3 audit; never accepts a prefix or initial gate.

Recomputes phase order, contact sums, target slew, rendering clocks and every
actual particle's membership. A passing audit still requires ROOT to view the
three phase snapshots from all three original videos before data admission.
"""
from __future__ import annotations
import argparse,hashlib,json,math,time
from pathlib import Path
import cv2,numpy as np
from native_liquid_cavity import Cavity,inverse_quat_points
from native_clock_contract_v60 import bind_initial_row,validate_recorded,validate_episode_binding
from initial_scene_review_v60 import validate_scene_admission,validate_available_native_pid_receipts

TASK='psibot_3_pour_restore_pads_v2';CAMERAS=['head_camera','chest_camera','third_camera']
JOINTS=[f'arm2_joint_link{i}'for i in range(1,8)]+[f'hand2_joint_link_{i}_1'for i in range(1,6)]+['hand2_joint_link_1_2']
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def require(condition,code):
    if not condition:raise ValueError(code)
def norm(v):return float(np.linalg.norm(v))
def angle(a,b):
    a=np.asarray(a);b=np.asarray(b);n=norm(a)*norm(b);require(n>1e-9,'invalid_relative_quaternion')
    return 2*math.acos(min(1.,abs(float(a@b))/n))
def released(row,key,pad):
    obj=row['objects'][key];target=row['supports'][pad]['center_world_m']
    return (obj['support_contact_points'].get(pad,0)>0 and obj['robot_contact_points']==0
            and norm(np.asarray(obj['link_position_world_m'])[:2]-target[:2])<=.020
            and abs(obj['bottom_world_z_m']-target[2])<=.008 and obj['tilt_deg']<=10
            and obj['hand_clearance_m']>=.030 and obj['hand_origin_clearance_m']>=.120
            and norm(obj['linear_velocity_m_s'])<.010 and norm(obj['angular_velocity_rad_s'])<.100)

class OrderedPhysics:
    def __init__(self,first):
        self.initial_native_tick=bind_initial_row(first)
        self.first=first;self.phase=0;self.times=[];self.ticks=[];self.carry_since=None
        self.carry_pose=None;self.carried=False;self.tilted=False;self.condition_since=None
        require(released(first,'A','rack_S1')and released(first,'B','rack_S2'),'initial_cups_not_released_original_pads')
        require(not any(first['objects'][k]['support_contact_points'].get('operation_tray',0)>0 for k in ['A','B']),'initial_third_pad_not_empty')
        n=first['liquid_counts']['total'];require(n>=200 and first['liquid_counts']['A']>=.95*n and first['liquid_counts']['B']==0,'initial_liquid_wrong')
        self.total=n
    def consume(self,row):
        tick=row['tick'];t=tick/120;obj=row['objects']['A'];b=row['objects']['B'];counts=row['liquid_counts']
        validate_recorded(row,self.initial_native_tick)
        require(row['native_contacts_observable']is True and row['all17_native_hand2_links_covered']is True,'native_observer_coverage_missing')
        require(row['whole_episode_task_actions_written_by_observer']is False,'observer_wrote_task_controls')
        require(not row['safety_violation']and row['native_report_min_separation_m']>=-.002,'full_native_safety_violation')
        require(b['support_contact_points'].get('rack_S2',0)>0 and b['tilt_deg']<=10
                and norm(np.asarray(b['link_position_world_m'])-self.first['objects']['B']['link_position_world_m'])<=.020,'B_preservation_failed')
        target=row['supports']['rack_S2']['center_world_m'];over=(norm(np.asarray(obj['link_position_world_m'])[:2]-target[:2])<=.070
              and obj['link_position_world_m'][2]>=target[2]+.095)
        require(obj['tilt_deg']<=(110 if over else 15),'A_tilt_outside_native_pour_envelope')
        require(counts['total']==self.total and counts['A']+counts['B']+counts['outside_vessels']==self.total
                and counts['in_transit']+counts['currently_spilled_outside']==counts['outside_vessels']
                and counts['spill']<=.02*self.total,'particle_conservation_or_spill_failed')
        held=(obj['hand_contact_points']>0 and sum(obj['support_contact_points'].values())==0
              and obj['link_position_world_m'][2]>=self.first['objects']['A']['link_position_world_m'][2]+.010)
        if held:
            rel=obj['object_pose_in_wrist']
            if self.carry_since is None:self.carry_since=t;self.carry_pose=rel
            if norm(np.asarray(rel['position_m'])-self.carry_pose['position_m'])>.005 or angle(rel['quaternion_wxyz'],self.carry_pose['quaternion_wxyz'])>math.radians(5):
                self.carry_since=t;self.carry_pose=rel
            if t-self.carry_since>=3-1e-6:self.carried=True
            if obj['tilt_deg']>=45:self.tilted=True
        else:self.carry_since=None;self.carry_pose=None
        if self.phase==3:
            require(released(row,'A','rack_S1')and released(row,'B','rack_S2'),'post_completion_preservation_failed');return
        if self.phase==0:condition=self.carried and self.carry_since is not None;duration=0
        elif self.phase==1:condition=self.tilted and self.carry_since is not None and counts['B']>=.95*self.total;duration=2
        else:condition=released(row,'A','rack_S1')and counts['B']>=.95*self.total;duration=3
        if not condition:self.condition_since=None;return
        if self.condition_since is None:self.condition_since=t
        if t-self.condition_since>=duration-1e-6:
            self.times.append(t);self.ticks.append(tick);self.phase+=1;self.condition_since=None
            if self.phase==3:
                require(released(row,'A','rack_S1')and released(row,'B','rack_S2'),'final_both_cups_not_released')

def contacts(row):
    roots={k:'/World/envs/env_0/Bottle'+k for k in ['A','B']}
    pads={k:'/World/envs/env_0/Support_'+k for k in row['supports']}
    totals={k:{'robot':0,'hand':0,'pads':{p:0 for p in pads}}for k in roots};minimum=0.
    def match(p,root):return p==root or p.startswith(root+'/')
    for r in row['native_contacts']:
        require(type(r['count'])is int and r['count']>0,'invalid_native_contact_count')
        sides=[(r['actor0'],r['collider0']),(r['actor1'],r['collider1'])]
        robot=[any(match(p,'/World/envs/env_0/Robot')for p in s)for s in sides]
        keys=[next((k for k,root in roots.items()if any(match(p,root)for p in s)),None)for s in sides]
        if any(robot)or any(k is not None for k in keys):minimum=min(minimum,r['minimum_separation_m'])
        for i,key in enumerate(keys):
            if key is None:continue
            other=sides[1-i]
            if robot[1-i]:totals[key]['robot']+=r['count']
            if any(p.startswith('/World/envs/env_0/Robot/hand2_')for p in other):totals[key]['hand']+=r['count']
            for pad,root in pads.items():
                if any(match(p,root)for p in other):totals[key]['pads'][pad]+=r['count']
    require(abs(minimum-row['native_report_min_separation_m'])<1e-9,'native_contact_separation_summary_mismatch')
    for key,o in row['objects'].items():
        require(o['robot_contact_points']==totals[key]['robot']and o['hand_contact_points']==totals[key]['hand']
                and o['support_contact_points']==totals[key]['pads'],'native_contact_summary_mismatch')

def audit(output,source,runtime,initial_review,capability_file):
    import h5py
    require(not(output/'FAILED_ATTEMPT_SEAL.json').exists(),'failed_whole_attempt_ineligible')
    require(not(output/'ORIGINAL_T3_ALL_TICK_PHYSICS_FAILED.json').exists(),'original_physics_failed')
    evaluation=load(output/'INTERNAL_EVALUATION_REQUIRING_ROOT_AUDIT.json')
    require(evaluation.get('success')is True and evaluation.get('stop_reason')=='task_complete','whole_task_not_complete')
    frozen=load(output/'SOURCE_MANIFEST.json');gate=load(output/'RUNTIME_GATE_AWAITING_ROOT.json');start=load(output/'MODEL_START_ADMISSION.json')
    require(gate['passed']is True and gate['task_id']==TASK,'native_source_gate_not_passed')
    require(frozen['source_sha256']==gate['source_sha256']==evaluation['source_sha256'],'native_source_identity_mismatch')
    actual={}
    for name,want in frozen['files'].items():
        require(not Path(name).is_absolute()and '..'not in Path(name).parts and name.startswith(('candidate/','runtime/')),'frozen_source_path_invalid')
        root=source if name.startswith('candidate/')else runtime;file=root/name.split('/',1)[1]
        actual[name]=sha(file);require(actual[name]==want,'frozen_native_source_changed')
    require(hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest()==frozen['source_sha256'],'frozen_native_manifest_hash_mismatch')
    review=validate_scene_admission(start,output,gate['source_sha256'],evaluation['episode_id'],initial_review)
    native_pid_receipts=validate_available_native_pid_receipts(output,gate['native_identity'])
    for name,item in gate['photos'].items():require(sha(output/item['file'])==item['sha256']==review['native_photo_sha256'][name],'native_initial_photo_changed')
    geometry=load(output/'NATIVE_FULL_HAND_OBSERVER_GEOMETRY.json')
    require(geometry['all17_hand_bodies_measured']is True and len(geometry['bodies'])==17,'native_full_hand_geometry_missing')
    records=load(output/'RECORDING_MANIFEST.json')
    rows=[json.loads(s)for s in(output/'evaluator_trace_120hz.jsonl').read_text().splitlines()]
    controls=[json.loads(s)for s in(output/'native_controls_120hz.jsonl').read_text().splitlines()]
    from direct_macro_provenance_v60 import provenance,runtime_source_digest
    require(runtime_source_digest(runtime)==frozen['source_sha256'],'source60_actual_file_set_changed')
    config=load(capability_file)
    if 'capability'not in config:config=config[evaluation['episode_id']]
    capability=config['capability']
    require(type(capability)is str and len(capability)==64 and all(c in '0123456789abcdef'for c in capability),'private_capability_invalid')
    macro_provenance,_=provenance(output,runtime,evaluation,rows,controls,capability)
    cursor=len(rows)-1
    require(records['last_tick']==cursor and records['native_physics_rows']==cursor+1,'whole_recording_macro_clock_mismatch')
    require(records['physics_hz']==120 and records['native_image_hz']==15 and records['frame_tick_stride']==8 and records['first_tick']==0 and records['native_particle_rows']==len(rows)and records['independent_joint_order']==JOINTS and records['inference_waits_advance_physics']is False,'native_recording_rate_changed')
    require(len(rows)==len(controls)==cursor+1,'whole_native_control_trace_missing')
    initial_public=load(output/'initial_observation/public_state.json')['robot']
    limits=np.asarray(initial_public['arm_joint_limits_rad']+initial_public['hand_joint_limits_rad'])
    require(limits.shape==(13,2)and np.isfinite(limits).all()and np.all(limits[:,0]<=limits[:,1]),'initial_native_hard_limits_invalid')
    validate_episode_binding(load(output/'NATIVE_CLOCK_CONTRACT.json'),rows[0],load(output/'DIRECT_CUROBO_INITIAL_STATE_RECEIPT.json'))
    phase=OrderedPhysics(rows[0]);cavity=Cavity(runtime/'T3_NATIVE_BEAKER_AUTHORED_COLLISION_MESH.json')
    require(phase.total==1290,'original_t3_particle_count_changed')
    require(cavity.mesh_sha256==gate['native_cavity']['mesh_json_sha256'],'actual_cavity_source_mismatch')
    spilled=np.zeros(phase.total,dtype=bool);previous=None
    with h5py.File(output/'actual_particle_positions_120hz.h5','r')as file:
        particles=file['positions_world_m'];require(particles.shape==(len(rows),phase.total,3),'actual_particle_recording_shape_wrong')
        for i,(row,control)in enumerate(zip(rows,controls)):
            require(row['tick']==control['tick']==i and control['ordered_joint_names']==JOINTS,'native_ticks_or_joint_order_changed')
            values=np.asarray([control['native_target13_rad'],control['measured_qpos13_rad'],control['measured_qvel13_rad_s']]);require(values.shape==(3,13)and np.isfinite(values).all(),'invalid_actual_native_joint_values')
            require(np.all(values[0]>=limits[:,0])and np.all(values[0]<=limits[:,1]),'actual_native_targets_outside_hard_limits')
            if previous is not None:require(np.all(np.abs(values[0]-previous)<=np.r_[np.full(7,.72/120+1e-6),np.full(6,1.2/120+1e-6)]),'actual_native_target_slew_failed')
            previous=values[0];contacts(row);p=particles[i];masks={}
            for k in ['A','B']:
                obj=row['objects'][k];masks[k]=cavity.contains_local(inverse_quat_points(p,obj['link_position_world_m'],obj['quaternion_world_wxyz']))
            require(not np.any(masks['A']&masks['B']),'overlapping_actual_vessel_cavities');inside=masks['A']|masks['B']
            spilled|=(~inside)&(p[:,2]<=row['objects']['B']['bottom_world_z_m']+.003)
            measured={'total':len(p),'A':int(masks['A'].sum()),'B':int(masks['B'].sum()),'outside_vessels':int((~inside).sum()),
                      'in_transit':int(((~inside)&(~spilled)).sum()),'spill':int(spilled.sum()),'currently_spilled_outside':int(((~inside)&spilled).sum())}
            require(measured==row['liquid_counts'],'actual_particle_vs_observer_count_mismatch');phase.consume(row)
            if i%8==0:
                alignment=row['render_alignment_evaluator_only'];require(alignment['robot_link_count']>=17,'renderer_link_coverage_missing')
                require(alignment['max_robot_position_error_m']<=1e-4 and alignment['max_robot_orientation_error_rad']<=1e-3
                        and all(x['position_m']<=1e-4 and x['orientation_rad']<=1e-3 for x in alignment['object_errors'].values()),'rendered_physics_alignment_failed')
    require(phase.phase==3 and len(evaluation['phase_times_s'])==3
            and np.allclose(phase.times,evaluation['phase_times_s'],rtol=0,atol=1e-6),'independent_ordered_phases_not_passed')
    frames=cursor//8+1;require(records['native_frames_each_camera']==frames,'native_video_clock_wrong')
    snapshots=output/'ROOT_PHASE_NATIVE_FRAMES';snapshots.mkdir(exist_ok=False);photos=[]
    chosen={min(frames-1,t//8):name for t,name in zip(phase.ticks,['pick_A','pour_A_into_B','restore_A'])}
    for camera in CAMERAS:
        video=output/(camera+'.mp4');cap=cv2.VideoCapture(str(video));require(cap.isOpened(),'native_video_not_decodable')
        require(abs(cap.get(cv2.CAP_PROP_FPS)-15)<1e-6,'native_video_not_15Hz');count=0
        while True:
            ok,bgr=cap.read()
            if not ok:break
            require(bgr.shape==(480,640,3),'native_video_shape_wrong')
            if count in chosen:
                name=chosen[count]+'__'+camera+'.png';path=snapshots/name;require(cv2.imwrite(str(path),bgr),'native_phase_frame_write_failed')
                photos.append({'file':str(path.relative_to(output)),'sha256':sha(path),'phase':chosen[count],'camera':camera,'native_frame_index':count,'native_tick':count*8})
            count+=1
        cap.release();require(count==frames,'native_video_frame_count_mismatch')
    require(len(photos)==9,'missing_all3_phases_all3_views')
    files={p.name:sha(p)for p in [output/'evaluator_trace_120hz.jsonl',output/'native_controls_120hz.jsonl',output/'actual_particle_positions_120hz.h5',output/'SOURCE_MANIFEST.json',output/'MODEL_REQUEST_LEDGER.json',output/'RECORDING_MANIFEST.json',output/'NATIVE_CLOCK_CONTRACT.json',output/'DIRECT_CUROBO_INITIAL_STATE_RECEIPT.json',output/'MODEL_START_ADMISSION.json',Path(initial_review),*[output/(k+'.mp4')for k in CAMERAS]]}
    return {'independent_physical_and_recording_audit_passed':True,'accepted_training_data':False,'whole_episode_accepted':False,
            'requires_ROOT_phase_visual_review':True,'task_version':TASK,'episode_id':evaluation['episode_id'],'seed':evaluation['seed'],
            'source_sha256':frozen['source_sha256'],'ordered_phase_times_s':phase.times,'phase_native_ticks':phase.ticks,
            'all_particle_rows_recomputed':len(rows),'actual_particle_count':phase.total,'decoded_original_frames_each_camera':frames,
            'independent_macro_provenance_audit_passed':True,'macro_provenance':macro_provenance,
            'numerical_clock_contract':load(output/'NATIVE_CLOCK_CONTRACT.json'),
            'initial_scene_reviewer_identity':review['reviewer_identity'],'new_model_generations':0,
            'native_identity':gate['native_identity'],'native_PID_receipts_checked':native_pid_receipts,
            'unique_native_episode_registry_required_before_admission':True,
            'source_files_verified':len(actual),'evidence_file_sha256':files,'phase_photos':photos,
            'independent_auditor_sha256':sha(Path(__file__)),'at_epoch':time.time()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--runtime',type=Path,required=True);p.add_argument('--initial-review',type=Path,required=True)
    p.add_argument('--capability-file',type=Path,required=True);a=p.parse_args()
    try:result=audit(a.output,a.source,a.runtime,a.initial_review,a.capability_file)
    except Exception as e:result={'independent_physical_and_recording_audit_passed':False,'accepted_training_data':False,
                               'whole_episode_accepted':False,'error_type':type(e).__name__,'failure':str(e),'at_epoch':time.time()}
    path=a.output/'INDEPENDENT_WHOLE_T3_AUDIT.json';path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ['phase_photos','evidence_file_sha256']},allow_nan=False))
if __name__=='__main__':main()
