"""CPU-only final closure of fixed paired50 cohorts; no unverified result is a failure."""
from pathlib import Path
import collections,hashlib,json,time
import numpy as np
S=Path('/project_a02012413/public/liyufeng/safelab_task10_new_variants_20261102/eval_v11_20261103')
V=S/'attach_stable_grasp_20261106/latched_native32_v6';A=S/'inference_enhancements_20261106';O=V/'operational_control_r3'
models=['mem0_original','ours_aligned','ours_aligned_weak']
protocols=['placement-v1.1','SafeLab-Eval-v1.2-relaxed','SafeLab-Eval-v1.3-lenient']
expected={(i,910100+i)for i in list(range(25))+list(range(50,75))}
packs={'R18':['R18','R25','R20','R21'],'R22':['R22','R23','R24']}
def atomic(path,value):
 q=path.with_suffix('.next');q.write_text(json.dumps(value,ensure_ascii=False,indent=2));q.replace(path)
def ci(values):
 v=np.array(values,dtype=float);idx=np.random.default_rng(20261106).integers(len(v),size=(10000,len(v)))
 return np.quantile(v[idx].mean(axis=1),[.025,.975]).tolist()
def close(label,labels):
 maps={m:{}for m in models};proof=[]
 for lab in labels:
  d=json.loads((O/(lab+'_WORKPACK.json')).read_text());r=Path(d['root'])/'cpu_verified_supportproof_r2'
  for f in r.glob('*.json'):
   raw=f.read_bytes();c=json.loads(raw)
   assert not c.get('unknown') and c['endpoint_slew_delivery_verified'] is True
   key=(c['scene_index'],c['seed']);assert key in expected
   proof.append({'source':str(f),'sha256':hashlib.sha256(raw).hexdigest()})
   old=maps[c['method']].get(key)
   if old is None or c['verified_epoch']<old['verified_epoch']:maps[c['method']][key]=c
 counts={m:len(v)for m,v in maps.items()}
 if any(v!=50 for v in counts.values()):return {'status':'pending','valid_by_method':counts}
 out={'stage':'diagnostic','formal_score_eligible':False,'source_cohort':label,'n_per_method':50,'bootstrap_seed':20261106,'bootstrap_replicates':10000,'unknown':0,'methods':{},'paired_TTC_minus_Mem0':{},'source_CPU_receipts':proof,'epoch':time.time()}
 for m in models:
  rows=[maps[m][k]for k in sorted(expected)];res={'n':50,'unknown':0,'ever_infrastructure_unknown':sum(bool(c.get('ever_infrastructure_unknown'))for c in rows),'attachment_triggered':sum(bool(c['attachment_triggered'])for c in rows),'protocols':{}}
  for p in protocols:
   phases=[c['protocols'][p]['phase']for c in rows];s=sum(bool(c['protocols'][p]['success'])for c in rows);half=3 if p==protocols[2]else 5
   res['protocols'][p]={'success':s,'mean_phase':float(np.mean(phases)),'mean_ci95':ci(phases),'hist':dict(sorted(collections.Counter(phases).items())),'half_success':sum(v>=half for v in phases),'direction_success':{order:sum(c['order']==order and bool(c['protocols'][p]['success'])for c in rows)for order in ['12345','54321']},'sensitivity_ever_unknown_as_failure':sum(bool(c['protocols'][p]['success'])and not c.get('ever_infrastructure_unknown')for c in rows)}
  out['methods'][m]=res
 for p in protocols:
  a=[maps[models[0]][k]['protocols'][p]for k in sorted(expected)];b=[maps[models[1]][k]['protocols'][p]for k in sorted(expected)]
  delta=np.array([y['phase']-x['phase']for x,y in zip(a,b)]);ds=np.array([int(y['success'])-int(x['success'])for x,y in zip(a,b)])
  out['paired_TTC_minus_Mem0'][p]={'paired_n':50,'paired_mean_difference':float(delta.mean()),'paired_mean_difference_ci95':ci(delta),'success_rate_difference':float(ds.mean()),'success_rate_difference_ci95':ci(ds)}
 atomic(A/(label+'_FINAL_THREE_METHODS50.json'),out)
 return {'status':'complete','valid_by_method':counts,'file':str(A/(label+'_FINAL_THREE_METHODS50.json')),'summary':{m:out['methods'][m]['protocols']for m in models},'paired_TTC_minus_Mem0':out['paired_TTC_minus_Mem0']}
while True:
 state={'epoch':time.time(),'cohorts':{k:close(k,v)for k,v in packs.items()}}
 atomic(O/'CURRENT_COHORT_FINALIZATION.json',state)
 print(json.dumps({'epoch':state['epoch'],'cohorts':{k:{x:v[x]for x in ['status','valid_by_method']}for k,v in state['cohorts'].items()}}),flush=True)
 if all(v['status']=='complete'for v in state['cohorts'].values()):break
 time.sleep(60)
