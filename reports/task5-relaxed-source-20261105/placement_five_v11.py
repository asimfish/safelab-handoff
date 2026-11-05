"""SafeLab-Eval-v1.1 five-task placement oracle, CPU-only offline path.

Original sequence, observed lift, XY25mm, upright0.97, catastrophic failure retained.
Support contact OR static height +/-5mm; no robot contact or active attachment;
30 consecutive120Hz updates debounce. No speed or pose-drift threshold.
Offline success is conservative: validate every final target at observed trace end.
Executor parity and video-backed negative admission remain separate gates.
"""
from pathlib import Path
import json,gzip,hashlib
import numpy as np
from scipy.spatial.transform import Rotation
VERSION='placement-v1.1-task5-20261103-v1'
SEQUENCE=[('A','temporary_A'),('B','temporary_B'),('C','target_C'),('A','pad_A'),('B','pad_B')]
SOURCES=['pad_A','pad_B','pad_C','temporary_A','temporary_B']
PARAMETERS=dict(dt_s=1/120,debounce_ticks=30,xy_tolerance_m=.025,upright_cos_min=.97,static_height_tolerance_m=.005,source_lift_fraction=.65,require_no_robot_contact=True,require_no_active_attachment=True,final_validation='allABC at final targets, at observed trace end; no optimistic early truncation')

def evaluate(profile,poses,support,no_robot,ticks):
 p=np.asarray(poses,dtype=np.float32);q=p[:,:,3:].astype(float);up=Rotation.from_quat(np.roll(q.reshape(-1,4),-1,axis=1)).apply(np.tile([0,0,1],(len(p)*3,1)))[:,2].reshape(-1,3)
 bad=(p[:,:,2]<profile['scene']['table_top']-.1).any(axis=1)|(up<.5).any(axis=1);failed=np.flatnonzero(bad);failure=int(failed[0])if len(failed)else len(p)
 events=[];start=0;phase_trace=np.zeros(len(p),dtype=int)
 def geometry(ix,target,sup,clear):
  key='ABC'[ix];bottom=profile['scene'].get('object_bottom_offsets',{}).get(key,profile['scene']['half_height']);center=np.asarray(profile['scene']['supports'][target])+[0,0,bottom]
  return(np.linalg.norm(p[:,ix,:2]-center[:2],axis=1)<=.025)&(up[:,ix]>=.97)&clear&(sup|(np.abs(p[:,ix,2]-center[2])<=.005))
 for phase,(key,target)in enumerate(SEQUENCE):
  ix='ABC'.index(key);bottom=profile['scene'].get('object_bottom_offsets',{}).get(key,profile['scene']['half_height']);source_z=profile['scene']['supports'][SOURCES[phase]][2]+bottom;lift=float(profile.get('stages',{}).get(str(phase+1),{}).get('lift_height',profile['motion']['lift_height']))
  lifted=np.flatnonzero(p[start:failure,ix,2]-source_z>=.65*lift)
  if not len(lifted):break
  first_lift=start+int(lifted[0]);geom=geometry(ix,target,support[:,phase],no_robot[:,ix]);invalid=np.r_[0,np.cumsum(~geom)];ends=np.flatnonzero(invalid[30:]-invalid[:-30]==0)+29;ends=ends[(ends>=max(start,first_lift)+29)&(ends<failure)]
  if not len(ends):break
  at=int(ends[0]);events.append(dict(phase=phase+1,tick=int(ticks[at]),object=key,target=target,debounce_ticks=30));phase_trace[at:]=phase+1;start=at+1
 final_ok=True
 for key,target,slot in[('A','pad_A',3),('B','pad_B',4),('C','target_C',2)]:
  ix='ABC'.index(key);final_ok=final_ok and bool(geometry(ix,target,support[:,slot],no_robot[:,ix])[-1])
 success=len(events)==5 and failure==len(p)and final_ok
 return dict(success=success,phase=len(events),events=events,irreversible_failure_tick=None if failure==len(p)else int(ticks[failure]),all_final_targets_valid=final_ok,phase_trace=phase_trace)

def rescore(item):
 contract=json.loads(Path(item['scene_contract']).read_text());path=Path(item['trace'])
 if not path.exists():path=Path(str(path)+'.gz')
 opener=gzip.open if path.suffix=='.gz'else open
 try:import orjson;decode=orjson.loads
 except ImportError:decode=json.loads
 poses=[];ticks=[];supports=[];no_robot=[];strict=[];digest=hashlib.sha256()
 with opener(path,'rb')as f:
  for line in f:
   digest.update(line);r=decode(line);poses.append(r['poses']);ticks.append(r['tick']);strict.append(r['physical_phase']);contacts=[c for c in r['contacts']if c['contact_count']>0];at=r.get('attachment');attached=at.get('attached_object')if isinstance(at,dict)else None
   if item['oracle_mode']=='attach'and not isinstance(at,dict):raise ValueError('missing attached state')
   supports.append([any(c['object']==key and'/'+target in c['actor']for c in contacts)for key,target in SEQUENCE]);no_robot.append([attached!=key and not any(c['object']==key and'/Robot/'in c['actor']for c in contacts)for key in'ABC'])
 assert poses and np.all(np.diff(ticks)==1),'tick gap or empty trace'
 if item.get('physics_sha256'):assert digest.hexdigest()==item['physics_sha256'],'source raw hash mismatch'
 p=np.asarray(poses,dtype=np.float32);p[:,:,:3]-=np.asarray(contract['env_origins'][0]);answer=evaluate(contract['source_profile'],p,np.asarray(supports,dtype=bool),np.asarray(no_robot,dtype=bool),np.asarray(ticks));answer.pop('phase_trace')
 return dict(id=item['id'],role=item['role'],variant=item['variant'],checkpoint=item.get('checkpoint_step'),horizon=item.get('execution_horizon'),condition=item['condition'],layout=item['layout'],seed=item.get('seed'),repeat=item.get('repeat'),status='rescored',protocol_version='SafeLab-Eval-v1.1',oracle_version='placement-v1.1',implementation_version=VERSION,formal_eligible=False,admission_pending=['executor_parity10','video_negatives10each'],strict_phase_from_previously_audited_trace=int(strict[-1]),strict_success_from_source=bool(json.loads((Path(item['episode_root'])/'RESULT.json').read_text()).get('success',False)),placement=answer,source_trace_sha256=digest.hexdigest(),oracle_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),parameters=PARAMETERS,source_rows=len(ticks))
