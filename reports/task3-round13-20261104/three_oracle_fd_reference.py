from pathlib import Path
import ast,json,math,hashlib,sys,copy
import numpy as np
R=Path(__file__).resolve().parent;SUPPORT=R/'support';ORACLE=SUPPORT/'audit_whole_t3_stream_liveness_v11.py';ORACLE_SHA='43d58adecd639cdcbc5ebbe71314503dbbebf14504fa24165452d4e4c9529721'
def quat_delta(q,p,dt):
 q=np.asarray(q,dtype=np.float64);p=np.asarray(p,dtype=np.float64)
 if q.shape!=(4,)or p.shape!=(4,)or not np.isfinite(q).all()or not np.isfinite(p).all()or not math.isfinite(dt)or dt<=0:raise ValueError('invalid_quaternion_or_dt')
 nq=np.linalg.norm(q);np_=np.linalg.norm(p)
 if min(nq,np_)<1e-12:raise ValueError('zero_quaternion')
 q=q/nq;p=p/np_
 if np.dot(q,p)<0:q=-q
 a,u=q[0],q[1:];b,v=p[0],-p[1:];real=a*b-np.dot(u,v);imag=a*v+b*u+np.cross(u,v);length=np.linalg.norm(imag)
 return imag*(2/dt if length<1e-12 else 2*math.atan2(length,max(0.,real))/(length*dt))
def fd_row(cur,prev):
 if cur['tick']!=prev['tick']+1 or cur['native_tick']!=prev['native_tick']+1:raise ValueError('FD_requires_consecutive_physical_ticks')
 dt=float(cur['actual_physics_elapsed_s'])-float(prev['actual_physics_elapsed_s'])
 if not math.isfinite(dt)or dt<=0:raise ValueError('FD_actual_time_not_monotonic')
 out={**cur,'objects':{}}
 for k,o in cur['objects'].items():
  p=prev['objects'][k];v=(np.asarray(o['link_position_world_m'],dtype=float)-np.asarray(p['link_position_world_m'],dtype=float))/dt
  w=quat_delta(o['quaternion_world_wxyz'],p['quaternion_world_wxyz'],dt)
  if not np.isfinite(v).all():raise ValueError('FD_position_not_finite')
  out['objects'][k]={**o,'linear_velocity_m_s':v.tolist(),'angular_velocity_rad_s':w.tolist()}
 return out,dt
def compile_strict():
 raw=ORACLE.read_bytes();assert hashlib.sha256(raw).hexdigest()==ORACLE_SHA
 names={'require','norm','angle','released','OrderedPhysics','contacts'};tree=ast.parse(raw.decode());nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name in names];sys.path.insert(0,str(SUPPORT))
 from native_clock_contract_v60 import bind_initial_row,validate_recorded
 ns={'np':np,'math':math,'bind_initial_row':bind_initial_row,'validate_recorded':validate_recorded};exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(ORACLE),'exec'),ns);return ns
class Judge:
 def __init__(self,ns):self.ns=ns;self.rec=None;self.error=None
 def consume(self,row):
  if self.error is not None:return
  try:
   if self.rec is None:self.rec=self.ns['OrderedPhysics'](row)
   self.ns['contacts'](row);self.rec.consume(row)
  except Exception as e:self.error=str(e)
 def result(self):return {'success':bool(self.rec and self.rec.phase==3 and self.error is None),'physical_phase':self.rec.phase if self.rec else None,'error':self.error,'phase_times':self.rec.times if self.rec else []}
def quantiles(a):
 if not a:return {'n':0,'p50':None,'p95':None,'p99':None}
 p=np.percentile(np.asarray(a),[50,95,99]);return {'n':len(a),'p50':float(p[0]),'p95':float(p[1]),'p99':float(p[2])}
def score(stream,expected_sha,expected_rows):
 ns=compile_strict();strict=Judge(ns);fd=Judge(ns);sha=hashlib.sha256();count=0;prev=None;first=None;dts=[];noise={k:{name:[]for name in('physx_linear','physx_angular','FD_linear','FD_angular')}for k in('A','B')};open_static={k:True for k in noise};diag={'hand_contact_rows':0,'held_rows':0,'max_lift_m':0.,'max_tilt_deg':0.,'max_B_fraction':0.};noise_window_s=1.0
 for raw in stream:
  sha.update(raw);row=json.loads(raw);count+=1
  if first is None:first=row
  if prev is not None and(row['tick']!=prev['tick']+1 or row['native_tick']!=prev['native_tick']+1):raise ValueError('trace_tick_gap')
  strict.consume(row)
  if prev is not None:
   current,dt=fd_row(row,prev);dts.append(dt)
   if count==2:
    # Boundary is one-sided forward FD, never zero-filled or PhysX substituted.
    initial={**first,'objects':{k:{**o,'linear_velocity_m_s':current['objects'][k]['linear_velocity_m_s'],'angular_velocity_rad_s':current['objects'][k]['angular_velocity_rad_s']}for k,o in first['objects'].items()}};fd.consume(initial)
   fd.consume(current)
   for k,o in row['objects'].items():
    pad='rack_S1'if k=='A'else'rack_S2'
    if o['robot_contact_points']or o['support_contact_points'].get(pad,0)<=0:open_static[k]=False
    if open_static[k]and row['sim_time_s']<=noise_window_s:
     for name,key,source in [('physx_linear','linear_velocity_m_s',o),('physx_angular','angular_velocity_rad_s',o),('FD_linear','linear_velocity_m_s',current['objects'][k]),('FD_angular','angular_velocity_rad_s',current['objects'][k])]:noise[k][name].append(float(np.linalg.norm(source[key])))
  o=row['objects']['A'];diag['hand_contact_rows']+=o['hand_contact_points']>0;lift=o['link_position_world_m'][2]-first['objects']['A']['link_position_world_m'][2];diag['max_lift_m']=max(diag['max_lift_m'],lift);diag['max_tilt_deg']=max(diag['max_tilt_deg'],o['tilt_deg']);diag['max_B_fraction']=max(diag['max_B_fraction'],row['liquid_counts']['B']/row['liquid_counts']['total']);diag['held_rows']+=o['hand_contact_points']>0 and sum(o['support_contact_points'].values())==0 and lift>=.010
  prev=row
 if count!=expected_rows:raise ValueError('source_row_count_mismatch')
 if sha.hexdigest()!=expected_sha:raise ValueError('source_trace_SHA_mismatch')
 if count<2:raise ValueError('FD_needs_two_actual_ticks')
 phase=strict.result()['physical_phase'];mode='undetermined'
 if phase==0 and diag['hand_contact_rows']==0 and diag['held_rows']==0:mode='no_hand_contact_or_grasp_observed'
 elif phase is not None and phase<2 and diag['held_rows']>0:mode='post_grasp_pour_incomplete'
 elif phase==2:mode='return_or_release_not_completed'
 return {'strict-v1':strict.result(),'strict-fdvel-v1':fd.result(),'trace_sha256':sha.hexdigest(),'trace_rows':count,'dt_actual_s':{'min':min(dts),'max':max(dts)},'FD_boundary':'tick0 uses forward difference from actual ticks0/1; all subsequent rows backward difference; no resampling','noise':{k:{n:quantiles(a)for n,a in metrics.items()}for k,metrics in noise.items()},'noise_window':{'sim_seconds':[0,1.0],'definition':'opening original-pad support with zero robot contact; truncate at first contact/support loss','certified_before_first_robot_action':False,'selection_does_not_filter_by_velocity':True},'failure_mode_observed':mode,'failure_observations':diag,'provisional_until_shared_task3_concordance':True,'strict_oracle_sha256':ORACLE_SHA,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
