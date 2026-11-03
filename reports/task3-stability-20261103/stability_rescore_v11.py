"""CPU-only diagnostic oracle variants. Never writes source traces or formal scores.

Requires a frozen threshold artifact; source oracle is compiled unchanged for v1,
with a single documented restoration-duration substitution for pose-drift only.
Stops at candidate completion (the original harness would stop there too).
"""
from pathlib import Path
from collections import deque
import ast, hashlib, json, math, sys
import numpy as np
SUPPORT=Path('/public_fast_storage/liyufeng/safelab_mem0_v13_eval_20261024/environment_support')
ORACLE=SUPPORT/'source/runtime/audit_whole_t3_stream_liveness_v11.py'
ORACLE_SHA='43d58adecd639cdcbc5ebbe71314503dbbebf14504fa24165452d4e4c9529721'
THRESHOLD_SHA='d841c5ccb7f0c728c6506083d3ab227a8b38250147b79f9e5e8fcf4d439f62aa'
def geometry(row,key,pad):
 o=row['objects'][key];p=row['supports'][pad]['center_world_m']
 return (o['support_contact_points'].get(pad,0)>0 and o['robot_contact_points']==0
  and np.linalg.norm(np.asarray(o['link_position_world_m'])[:2]-p[:2])<=.020
  and abs(o['bottom_world_z_m']-p[2])<=.008 and o['tilt_deg']<=10
  and o['hand_clearance_m']>=.030 and o['hand_origin_clearance_m']>=.120)
class Window:
 def __init__(self,threshold):
  self.threshold=threshold;self.rows=deque();self.qprevious={};self.phase2_tick=None
 def push(self,row,phase):
  tick=row['tick']
  if phase==2 and self.phase2_tick is None:self.phase2_tick=tick
  item={'tick':tick,'objects':{},'liquid':row['liquid_counts']['B']>=.95*row['liquid_counts']['total']}
  for key,pad in [('A','rack_S1'),('B','rack_S2')]:
   o=row['objects'][key];q=np.array(o['quaternion_world_wxyz'],dtype=float);q/=np.linalg.norm(q)
   if key in self.qprevious and np.dot(q,self.qprevious[key])<0:q=-q
   self.qprevious[key]=q
   item['objects'][key]={'p':o['link_position_world_m'],'q':q,'angular':float(np.linalg.norm(o['angular_velocity_rad_s'])),'geometry':geometry(row,key,pad)}
  self.rows.append(item)
  while self.rows and self.rows[0]['tick']<tick-360:self.rows.popleft()
 def pose_stable(self,key):
  if len(self.rows)!=361 or self.rows[-1]['tick']-self.rows[0]['tick']!=360:return False
  v=[r['objects'][key] for r in self.rows]
  p=np.array([r['p'] for r in v]);q=np.array([r['q'] for r in v]);d=float(np.linalg.norm(np.ptp(q,axis=0)))
  return (np.linalg.norm(np.ptp(p,axis=0))<=self.threshold['position_range_m']
   and min(math.pi,4*math.asin(min(1,d/2)))<=self.threshold['rotation_range_rad'])
 def restore(self,row,rec):
  return (self.phase2_tick is not None and self.rows[0]['tick']>=self.phase2_tick
   and self.pose_stable('A') and all(r['objects']['A']['geometry'] and r['liquid'] for r in self.rows))
 def released(self,row,key,pad,mode,original):
  if mode=='original':return original(row,key,pad)
  if mode=='pose':return geometry(row,key,pad) and self.pose_stable(key)
  v=[r['objects'][key]['angular'] for r in self.rows if r['tick']>=row['tick']-60]
  return (len(v)==61 and geometry(row,key,pad) and np.linalg.norm(row['objects'][key]['linear_velocity_m_s'])<.010 and sum(v)/len(v)<.100)
def compile_oracle(mode,window):
 raw=ORACLE.read_bytes();assert hashlib.sha256(raw).hexdigest()==ORACLE_SHA,'oracle changed'
 sys.path.insert(0,str(SUPPORT/'source/runtime'))
 from native_clock_contract_v60 import bind_initial_row,validate_recorded
 src=raw.decode()
 if mode=='pose':
  before="else:condition=released(row,'A','rack_S1')and counts['B']>=.95*self.total;duration=3"
  assert src.count(before)==1
  src=src.replace(before,'else:condition=candidate_restore(row,self);duration=0')
 tree=ast.parse(src);names={'require','norm','angle','released','OrderedPhysics','contacts'}
 nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
 ns={'np':np,'math':math,'bind_initial_row':bind_initial_row,'validate_recorded':validate_recorded,'candidate_restore':window.restore}
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ORACLE),'exec'),ns)
 return ns

def rescore(trace,threshold_path,expected_rows=None):
 threshold_raw=Path(threshold_path).read_bytes();assert hashlib.sha256(threshold_raw).hexdigest()==THRESHOLD_SHA
 threshold=json.loads(threshold_raw);modes={};sha=hashlib.sha256();count=0;previous=None
 for mode in ['original','pose','angular_mean']:
  w=Window(threshold);ns=compile_oracle(mode,w)
  modes[mode]={'window':w,'ns':ns,'rec':None,'done':False,'error':None}
 with Path(trace).open('rb') as f:
  for raw in f:
   sha.update(raw);row=json.loads(raw);tick=row['tick'];count+=1
   if previous is not None and tick!=previous+1:raise ValueError('trace_tick_gap')
   previous=tick
   for mode,item in modes.items():
    if item['done']:continue
    ns=item['ns'];w=item['window']
    try:
     if item['rec'] is None:
      rec=ns['OrderedPhysics'](row);item['rec']=rec
      original=ns['released'];ns['released']=lambda r,k,p,m=mode,w=w,o=original:w.released(r,k,p,m,o)
     rec=item['rec'];w.push(row,rec.phase);ns['contacts'](row);rec.consume(row)
     if rec.phase==3:item['done']=True
    except Exception as exc:item['error']=str(exc);item['done']=True
 if expected_rows is not None and count!=expected_rows:raise ValueError('trace_row_count_mismatch')
 result={}
 for mode,item in modes.items():
  rec=item['rec'];result[mode]={'success':bool(rec and rec.phase==3 and item['error'] is None),'phase':rec.phase if rec else None,'phase_times':rec.times if rec else [],'error':item['error']}
 return {'stage':'diagnostic','metric_role':'rescored_v1.1_candidate','threshold_sha256':THRESHOLD_SHA,'oracle_sha256':ORACLE_SHA,'trace_sha256':sha.hexdigest(),'trace_rows':count,'variants':result,'censoring':'stop each variant at its own completion or first invariant failure; source prefix only; no counterfactual beyond recorded end'}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('trace');p.add_argument('thresholds');p.add_argument('--expected-rows',type=int);p.add_argument('--output');a=p.parse_args()
 result=rescore(a.trace,a.thresholds,a.expected_rows);text=json.dumps(result,indent=2)+'\n'
 if a.output:Path(a.output).write_text(text)
 print(text)
