from pathlib import Path
import json,hashlib,time
import numpy as np
S=Path('/project_a02012413/public/liyufeng/safelab_task10_new_variants_20261102/eval_v11_20261103');V6=S/'attach_stable_grasp_20261106/latched_native32_v6';AUD=S/'inference_enhancements_20261106'
ROOTS={'D':[V6/'three_methods_h4_first50'],'measured_hold':[V6/'r6_latched_finger_hold_h4_first50'],'measured_hold_slew':[V6/'r9_finger_hold_expert_slew_h4_first50'],'command_hold':[V6/'r12_finger_hold_last_command_h4_first50'],'command_hold_slew':[V6/'r13_hold_last_command_expert_slew_h4_first50',V6/'r16_same_seed_R13_continuation'],'command_hold_slew_h2':[V6/'r14_hold_last_command_expert_slew_h2_first50',V6/'r15_same_seed_r14_retry10',V6/'r17_second_R14_retry10',V6/'r19_third_R14_retry7']}
plans=[('measured_hold','D'),('measured_hold_slew','measured_hold'),('command_hold','measured_hold'),('command_hold_slew','measured_hold_slew'),('command_hold_slew','command_hold'),('command_hold_slew_h2','command_hold_slew')]
methods=['mem0_original','ours_aligned','ours_aligned_weak'];protocols=['placement-v1.1','SafeLab-Eval-v1.2-relaxed','SafeLab-Eval-v1.3-lenient'];wanted=set(range(25))|set(range(50,75));loaded={}
for key,roots in ROOTS.items():
 data={m:{}for m in methods}
 seen=set()
 paths=[p for root in roots for p in (root/'cpu_verified_supportproof_r2').glob('*.json')]
 paths.sort(key=lambda p:json.loads(p.read_text())['verified_epoch'])
 for p in paths:
  d=json.loads(p.read_text())
  if d.get('CPU_verified') and not d.get('unknown') and d.get('horizon')==(2 if key.endswith('_h2')else 4) and d['scene_index']in wanted:
   m=d['method'];i=d['scene_index']
   if i in data[m]:continue
   assert d['seed']==910100+i;d['_source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();data[m][i]=d
 loaded[key]=data
out={'stage':'diagnostic','metric_role':'inference_side_enhancement','formal_score_eligible':False,'cohort':'frozen50,forward25reverse25','scene_list_hash':'c30224758a91c52679a7273884f71e17a39c6c09c478c9a9d168512207295a85','bootstrap_seed':20261106,'bootstrap_replicates':10000,'resampling_unit':'paired scene','protocol_units':{protocols[0]:10,protocols[1]:10,protocols[2]:5},'comparisons':[],'epoch':time.time()}
for candidate,reference in plans:
 for method in methods:
  a=loaded[reference][method];b=loaded[candidate][method];item={'candidate':candidate,'reference':reference,'method':method,'candidate_valid':len(b),'reference_valid':len(a),'paired_n':len(set(a)&set(b))}
  if set(a)!=wanted or set(b)!=wanted:item['status']='pending_full_balanced50_no_partial_effect_estimate';out['comparisons'].append(item);continue
  scenes=sorted(wanted);item['status']='complete';item['unknown']=0;item['paired_case_SHA256']=[{'scene':i,'seed':910100+i,'reference':a[i]['_source_sha256'],'candidate':b[i]['_source_sha256']}for i in scenes];item['protocols']={};idx=np.random.default_rng(20261106).integers(50,size=(10000,50))
  for protocol in protocols:
   aa=np.array([a[i]['protocols'][protocol]['phase']for i in scenes]);bb=np.array([b[i]['protocols'][protocol]['phase']for i in scenes]);da=bb-aa;sa=np.array([a[i]['protocols'][protocol]['success']for i in scenes],dtype=int);sb=np.array([b[i]['protocols'][protocol]['success']for i in scenes],dtype=int);ds=sb-sa
   item['protocols'][protocol]={'reference_success':int(sa.sum()),'candidate_success':int(sb.sum()),'reference_mean_phase':float(aa.mean()),'candidate_mean_phase':float(bb.mean()),'paired_mean_difference':float(da.mean()),'paired_mean_difference_ci95':np.quantile(da[idx].mean(axis=1),[.025,.975]).tolist(),'success_rate_difference':float(ds.mean()),'success_rate_difference_ci95':np.quantile(ds[idx].mean(axis=1),[.025,.975]).tolist()}
  out['comparisons'].append(item)
p=AUD/'INFERENCE_FACTORIAL_PAIRED50.json';tmp=p.with_suffix('.next');tmp.write_text(json.dumps(out,separators=(',',':')));tmp.replace(p);print(json.dumps({'completed_comparisons':sum(x['status']=='complete'for x in out['comparisons']),'planned_comparisons':len(out['comparisons']),'report_bytes':p.stat().st_size}))
