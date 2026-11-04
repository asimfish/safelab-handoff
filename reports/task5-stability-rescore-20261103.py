"""CPU-only five-task candidate, source trace immutable. No online oracle changes."""
from pathlib import Path
import json,gzip,hashlib
import numpy as np
from scipy.spatial.transform import Rotation
SEQ=[('A','temporary_A'),('B','temporary_B'),('C','target_C'),('A','pad_A'),('B','pad_B')]
SOURCES=['pad_A','pad_B','pad_C','temporary_A','temporary_B']

def load_case(item):
 contract=json.loads(Path(item['scene_contract']).read_text());path=Path(item['trace'])
 if not path.exists():path=Path(str(path)+'.gz')
 if not path.exists():raise FileNotFoundError('raw trace unavailable; no guessed candidate score')
 opener=gzip.open if path.suffix=='.gz'else open;poses=[];ticks=[];geom_contacts=[];attached=[];phase=[];digest=hashlib.sha256()
 try:import orjson;decode=orjson.loads
 except ImportError:decode=json.loads
 targets=[x[1]for x in SEQ]
 with opener(path,'rb')as f:
  for line in f:
   digest.update(line);r=decode(line);poses.append(r['poses']);ticks.append(r['tick']);phase.append(r['physical_phase']);con=r['contacts'];fingers=[];supports=[]
   for key,target in SEQ:
    c=[x for x in con if x['object']==key and x['contact_count']>0];supports.append(any('/'+target in x['actor']for x in c));fingers.append(any('/Robot/'in x['actor']and'/hand2_'in x['actor']for x in c))
   geom_contacts.append([s and not h for s,h in zip(supports,fingers)])
   at=r.get('attachment');active=at.get('attached_object')if isinstance(at,dict)else None
   if item['oracle_mode']=='attach'and not isinstance(at,dict):raise ValueError('missing attachment state; cannot ignore fixed constraint')
   attached.append([active==key for key,_ in SEQ])
 assert poses and np.all(np.diff(ticks)==1),'empty trace or physical tick gap'
 if item.get('physics_sha256'):assert digest.hexdigest()==item['physics_sha256'],'raw identity mismatch'
 p=np.asarray(poses,dtype=np.float32);p[:,:,:3]-=np.asarray(contract['env_origins'][0]);q=p[:,:,3:].astype(np.float64);q/=np.linalg.norm(q,axis=2)[:,:,None]
 ups=Rotation.from_quat(np.roll(q.reshape(-1,4),-1,axis=1)).apply(np.tile([0,0,1],(q.shape[0]*3,1)))[:,2].reshape(-1,3)
 return contract,p,q,ups,np.asarray(geom_contacts,dtype=bool)&~np.asarray(attached,dtype=bool),np.asarray(ticks),np.asarray(phase),digest.hexdigest(),str(path)

def stable_at(p,q,ends,threshold,mode):
 result=[]
 # Bound scratch memory to a few MiB regardless of episode duration.
 for chunk in np.array_split(ends,max(1,int(np.ceil(len(ends)/256)))):
  if not len(chunk):continue
  idx=chunk[:,None]-np.arange(120,-1,-1)[None,:];pw=p[idx];qw=q[idx]
  if mode=='original':
   drift=np.linalg.norm(pw-p[chunk,None,:],axis=2).max(axis=1)
   # Relative quaternion magnitude matches scipy Rotation magnitude without acos cancellation.
   a=np.broadcast_to(q[chunk,None,:],qw.shape);aw=a[:,:,0];av=a[:,:,1:];bw=qw[:,:,0];bv=qw[:,:,1:]
   vec=aw[:,:,None]*bv-bw[:,:,None]*av-np.cross(av,bv);w=aw*bw+(av*bv).sum(axis=2)
   angle=2*np.arctan2(np.linalg.norm(vec,axis=2),np.abs(w)).max(axis=1)
   good=(drift<=.001)&(angle<=.02)
  else:
   drift=np.linalg.norm(np.ptp(pw,axis=1),axis=1)
   angle=np.minimum(np.pi,4*np.arcsin(np.minimum(1,np.linalg.norm(np.ptp(qw,axis=1),axis=1)/2)))
   good=(drift<=threshold['position_range_m'])&(angle<=threshold['rotation_range_rad'])
  result.extend(chunk[good].tolist())
 return result

def score(profile,p,q,ups,contacts,ticks,threshold,mode):
 n=len(ticks);bad=(p[:,:,2]<profile['scene']['table_top']-.1).any(axis=1)|(ups<.5).any(axis=1);hits=np.flatnonzero(bad);fail=int(hits[0])if len(hits)else n;start=0;events=[];pending=0;phase_trace=np.zeros(n,dtype=int)
 q=q.copy()
 for j in range(3):
  sign=np.ones(n);sign[1:]=np.cumprod(np.where(np.sum(q[1:,j]*q[:-1,j],axis=1)<0,-1,1));q[:,j]*=sign[:,None]
 for phase,(key,target)in enumerate(SEQ):
  ix='ABC'.index(key);bottom=profile['scene'].get('object_bottom_offsets',{}).get(key,profile['scene']['half_height']);sz=profile['scene']['supports'][SOURCES[phase]][2]+bottom;lift=float(profile.get('stages',{}).get(str(phase+1),{}).get('lift_height',profile['motion']['lift_height']))
  lifts=np.flatnonzero(p[start:fail,ix,2]-sz>=.65*lift)
  if not len(lifts):break
  lifted=start+int(lifts[0]);center=np.asarray(profile['scene']['supports'][target])+[0,0,bottom]
  geom=(np.linalg.norm(p[:,ix,:2]-center[:2],axis=1)<=.025)&(np.abs(p[:,ix,2]-center[2])<=.012)&(ups[:,ix]>=.97)&contacts[:,phase]
  invalid=np.r_[0,np.cumsum(~geom)];ends=np.flatnonzero(invalid[121:]-invalid[:-121]==0)+120;ends=ends[(ends>=max(start,lifted)+120)&(ends<fail)];pending=len(ends)
  accepts=stable_at(p[:,ix,:3],q[:,ix],ends,threshold['thresholds_by_object'][key],mode)
  if not accepts:break
  at=accepts[0];events.append(dict(phase=phase+1,tick=int(ticks[at]),object=key,target=target));phase_trace[at:]=phase+1;start=at+1;pending=0
  if phase==4:
   for k in'ABC':
    if k==key:continue
    j='ABC'.index(k);last={'A':'pad_A','B':'pad_B','C':'target_C'}[k];c=np.asarray(profile['scene']['supports'][last])+[0,0,profile['scene']['object_bottom_offsets'][k]]
    if np.linalg.norm(p[at,j,:2]-c[:2])>.025 or abs(p[at,j,2]-c[2])>.012 or ups[at,j]<.97:return dict(success=False,phase=5,events=events,failure='other_beaker_not_restored',trace=phase_trace,pending_geometry_windows=0)
   return dict(success=True,phase=5,events=events,failure=None,trace=phase_trace,pending_geometry_windows=0)
 return dict(success=False,phase=len(events),events=events,failure='object_fell_or_toppled'if fail<n else None,trace=phase_trace,pending_geometry_windows=pending)

def rescore(item,threshold_path,expected_sha):
 raw=Path(threshold_path).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected_sha,'threshold changed after freezing';threshold=json.loads(raw);contract,p,q,ups,contacts,ticks,recorded,sha,path=load_case(item)
 strict=score(contract['source_profile'],p,q,ups,contacts,ticks,threshold,'original');assert np.array_equal(strict.pop('trace'),recorded),'vectorized original disagrees with independently audited per-tick phases'
 if item.get('physical_phases')is not None:assert strict['phase']==item['physical_phases']
 candidate=score(contract['source_profile'],p,q,ups,contacts,ticks,threshold,'pose');candidate.pop('trace')
 return dict(id=item['id'],role=item['role'],variant=item['variant'],checkpoint_step=item.get('checkpoint_step'),horizon=item.get('execution_horizon'),condition=item['condition'],layout=item['layout'],seed=item.get('seed'),repeat=item.get('repeat'),status='rescored',metric_role='rescored_v1.1_candidate',stage='diagnostic',source_trace_sha256=sha,source_threshold_sha256=expected_sha,source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=len(ticks),strict=strict,candidate=candidate,angular_mean_control=None,angular_mean_reason=threshold['angular_mean_control']['reason'],physical_placement_only_stability_blocked=strict['failure']is None and strict['pending_geometry_windows']>0 and candidate['phase']>strict['phase'],censoring='same source prefix, same irreversible failure and geometry/contact constraints; no extension past stored end')
