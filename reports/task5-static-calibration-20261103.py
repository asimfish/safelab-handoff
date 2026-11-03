"""CPU-only five-task static calibration. Freeze before any candidate rescoring."""
from pathlib import Path
import argparse,json,hashlib,time
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

def bounds(p,q,ticks):
 ps=sliding_window_view(p,ticks,axis=0);qs=sliding_window_view(q,ticks,axis=0)
 pos=np.linalg.norm(np.ptp(ps,axis=2),axis=1)
 rotation=np.minimum(np.pi,4*np.arcsin(np.minimum(1,np.linalg.norm(np.ptp(qs,axis=2),axis=1)/2)))
 end_pos=np.linalg.norm(ps-p[ticks-1:,:,None],axis=1).max(axis=1)
 dot=np.abs((qs*q[ticks-1:,:,None]).sum(axis=1));end_angle=2*np.arccos(np.clip(dot,-1,1)).max(axis=1)
 return pos,rotation,end_pos,end_angle

def quant(x):return {k:float(np.percentile(x,v))for k,v in [('p50',50),('p95',95),('p99',99)]}
def main(root,out):
 out.mkdir(parents=True,exist_ok=True);samples=[];identities=[];physics=[]
 for i in range(2):
  p=root/'runs'/('static_%d'%i);r=json.loads((p/'RESULT.json').read_text());assert r['complete']and r['rows']==601 and r['model_actions']==0 and r['unchanged_hold_targets']
  raw=(p/'static_120hz.jsonl').read_bytes();rows=[json.loads(x)for x in raw.splitlines()];assert len(rows)==601 and all(row['relative_tick']==j for j,row in enumerate(rows))
  identities.append(dict(scene=i,profile=r['profile'],trace_sha256=hashlib.sha256(raw).hexdigest(),native_initial_tick=r['initial_tick'],observation='five-second default hold before any model action; independent diagnostic, not added to formal episodes'))
  physics.append(json.loads((p/'PHYSX_OBJECT_METADATA.json').read_text()))
  samples.append({k:np.asarray([row['objects_root_link_state_w'][k][0]for row in rows],dtype=np.float64)for k in'ABC'})
 stats={};thresholds={};validation={}
 for key,kind in [('A','beaker1'),('B','flask1'),('C','beaker2')]:
  linear=[];angular=[];onepos=[];onerot=[];threepos=[];threerot=[];endp=[];endr=[]
  for scene in samples:
   x=scene[key];p=x[:,:3];q=x[:,3:7].copy();q/=np.linalg.norm(q,axis=1)[:,None];sgn=np.ones(len(q));sgn[1:]=np.cumprod(np.where(np.sum(q[1:]*q[:-1],axis=1)<0,-1,1));q*=sgn[:,None]
   linear.extend(np.linalg.norm(x[:,7:10],axis=1));angular.extend(np.linalg.norm(x[:,10:13],axis=1))
   p1,r1,e1,a1=bounds(p,q,121);p3,r3,_,_=bounds(p,q,361);onepos.extend(p1);onerot.extend(r1);threepos.extend(p3);threerot.extend(r3);endp.extend(e1);endr.extend(a1)
  stats[key]=dict(object_kind=kind,support='table pads',native_linear_speed_m_s=quant(linear),native_angular_speed_rad_s=quant(angular),position_range_1s_m=quant(onepos),rotation_range_1s_rad=quant(onerot),position_range_3s_m=quant(threepos),rotation_range_3s_rad=quant(threerot),position_endpoint_max_1s_m=quant(endp),rotation_endpoint_max_1s_rad=quant(endr),static_windows_1s=len(onepos),static_windows_3s=len(threepos))
  th=dict(position_range_m=max(.002,3*stats[key]['position_range_1s_m']['p99']),rotation_range_rad=max(.02,3*stats[key]['rotation_range_1s_rad']['p99']));thresholds[key]=th
  validation[key]=dict(original_static_stable_fraction=float(np.mean((np.asarray(endp)<=.001)&(np.asarray(endr)<=.02))),candidate_static_stable_fraction=float(np.mean((np.asarray(onepos)<=th['position_range_m'])&(np.asarray(onerot)<=th['rotation_range_rad']))))
 artifact=dict(version='task5-stability-v1.1-candidate-20261103-v1',metric_role='rescored_v1.1_candidate',epoch_frozen=time.time(),task='5b_obstruction',planned_static_scenes=4,valid_calibration_scenes=2,calibration_layouts=['forward','reverse'],infrastructure_censoring='scene2 interrupted by shared-host memory guard; scene3 unlaunched; firsttwo complete retained before statistics computed',dt_s=1/120,stable_ticks=121,elapsed_window_s=1.0,thresholds_by_object=thresholds,calibration_sources=identities,static_statistics=stats,static_validation=validation,position_method='L2 norm of per-axis bounding-box ranges, conservative full-window diameter bound',orientation_method='continuous-sign unit quaternion axis range bound min(pi,4asin(min(1,L2(ptp(q))/2))) reused from supplied three-task CPU tool',angular_mean_control=dict(applicable=False,reason='five-task checked original oracle has no angular-velocity threshold; do not invent an original threshold or transplant three-task0.1rad/s'),geometry_and_failure_rules_unchanged=True,oven_statistics='not applicable: this dataset is table-pad obstruction5b',source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 assert all(v['candidate_static_stable_fraction']>=.99 for v in validation.values())
 dest=out/'FROZEN_THRESHOLDS.json';raw=(json.dumps(artifact,sort_keys=True,indent=2)+'\n').encode()
 if dest.exists():raise FileExistsError('frozen threshold already exists; never refit after rescoring')
 with dest.open('xb')as f:f.write(raw)
 (out/'FROZEN_THRESHOLD_SHA.json').write_text(json.dumps(dict(sha256=hashlib.sha256(raw).hexdigest(),frozen_before_rescoring=True),indent=2)+'\n')
 (out/'PHYSX_OBJECT_METADATA_ALL4.json').write_text(json.dumps(physics,indent=2)+'\n')
 print(json.dumps(dict(frozen_sha256=hashlib.sha256(raw).hexdigest(),thresholds=thresholds,validation=validation)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.root,a.output)
