from pathlib import Path
import json,hashlib,sys,os,concurrent.futures,time,importlib.util,math
Q=Path(__file__).parent
R=Path('/public_fast_storage/liyufeng/safelab_mem0_five_seed_pro8_20261029')
OUT=Q/'r13_fd_reference_cases'
REF=Path('/project_a02012413/public/liyufeng/safelab_pi05_40k_20261101/safelab_eval_v1/round16/fdvel_cpu/three_oracle_fd.py')
REFSHA='c95086996df5a9e91b250b651541c203470e21ab963874ff7715c1c48ed6e69f'
TOL=1e-10

def lines(stream):
 buf=b''
 while True:
  block=stream.read(1048576)
  if not block:break
  buf+=block;parts=buf.split(b'\n');buf=parts.pop()
  for x in parts:yield x+b'\n'
 if buf:yield buf

def one(job):
 import numpy as np
 from fd_velocity_strict_v1 import fd_pair,SUPPORT
 case=job['case'];method=job['method'];seed=job['inference_seed']
 dst=OUT/(method+'_s'+str(seed)+'_'+case['id']+'.json')
 if dst.exists():return json.loads(dst.read_text())
 base={k:job[k]for k in ['method','inference_seed','side','scene_seed','model_seed']};base.update(case_id=case['id'],source_result_sha256=case['result_sha256'],source_trace_sha256=case['trace_sha256'])
 if case['unknown']:
  base.update(unknown=True,reason='source_episode_closure_unknown_not_retried');dst.write_text(json.dumps(base));return base
 assert hashlib.sha256(REF.read_bytes()).hexdigest()==REFSHA
 spec=importlib.util.spec_from_file_location('reference_fd',REF);ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
 # Only rebind support location, oracle bytes remain pinned to identical SHA.
 ref.SUPPORT=SUPPORT;ref.ORACLE=SUPPORT/'audit_whole_t3_stream_liveness_v11.py'
 if method=='mem0'and seed>0:
  folder=Q/f'mem0_paired_B_seed{seed}_r10g4/root/runs'/case['id']/'env_0'
  ar=json.loads((folder/'BOS_RAW_ARCHIVE.json').read_text());assert ar['passed']and ar['result_sha256']==case['result_sha256']
  key=next(x['key']for x in ar['files']if x['key'].endswith('/evaluator_trace_120hz.jsonl'))
  from r10_bos_archive import Archive
  a=Archive();stream=a.client.get_object(a.bucket,key).data
 else:
  roots=([R/'evalv1_mem0_v13_trainresize_full_r6b/stageA/run',R/'evalv1_mem0_v13_trainresize_full_r6b/smoke/run']if method=='mem0'else[R/'evalv1_ours_trainresize_stageA_r2/stageA/run',R/'evalv1_ours_trainresize_stageA_r2/smoke/run']if seed==0 else[R/f'evalv1_ttc_trainresize_stageB_seed{seed}_r6b/bundle/run'])
  folder=next(f for r in roots if(f:=r/'runs'/case['id']/'env_0'/'evaluator_trace_120hz.jsonl').is_file()).parent
  stream=(folder/'evaluator_trace_120hz.jsonl').open('rb')
 raw=(folder/'RESULT.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==case['result_sha256'];result=json.loads(raw)
 cached=json.loads((Q/'fd_v1_a08_h8_seed012'/(method+'_s'+str(seed)+'_'+case['id']+'.json')).read_text())
 noise={k:{n:[]for n in ['physx_linear','physx_angular','FD_linear','FD_angular']}for k in ['A','B']};active={'A':True,'B':True};maximum={'linear':0.,'angular':0.};pair_count=0
 def checked():
  nonlocal pair_count
  previous=None
  for rawline in lines(stream):
   row=json.loads(rawline)
   if previous is not None:
    own=fd_pair(previous,row);rr,dt=ref.fd_row(row,previous);pair_count+=1
    for k,o in row['objects'].items():
     for short,key in [('linear','linear_velocity_m_s'),('angular','angular_velocity_rad_s')]:maximum[short]=max(maximum[short],max(abs(x-y)for x,y in zip(own[k][key],rr['objects'][k][key])))
     pad='rack_S1'if k=='A'else'rack_S2'
     if o['robot_contact_points']or o['support_contact_points'].get(pad,0)<=0:active[k]=False
     if active[k]and row['sim_time_s']<=1.0:
      for name,key,obj in [('physx_linear','linear_velocity_m_s',o),('physx_angular','angular_velocity_rad_s',o),('FD_linear','linear_velocity_m_s',rr['objects'][k]),('FD_angular','angular_velocity_rad_s',rr['objects'][k])]:noise[k][name].append(float(np.linalg.norm(obj[key])))
   previous=row;yield rawline
 try:scored=ref.score(checked(),case['trace_sha256'],result['native_rows'])
 finally:stream.close()
 fd=scored['strict-fdvel-v1'];phase_equal=fd['physical_phase']==cached['physical_phase'];times_equal=len(fd['phase_times'])==len(cached['phase_times'])and all(abs(x-y)<1e-9 for x,y in zip(fd['phase_times'],cached['phase_times']))
 base.update(unknown=False,reference_FD=fd,our_FD={k:cached.get(k)for k in ['success','physical_phase','phase_times','error']},strict_reference=scored['strict-v1'],strict_source=case['strict_success'],success_equal=fd['success']==cached['success'],phase_equal=phase_equal,phase_times_equal=times_equal,strict_success_equal=scored['strict-v1']['success']==case['strict_success'],maximum_velocity_abs_difference=maximum,numeric_tolerance=TOL,numeric_pass=max(maximum.values())<=TOL,adjacent_pairs=pair_count,noise=scored['noise'],noise_raw_samples=noise,noise_window=scored['noise_window'])
 dst.write_text(json.dumps(base));return base

def main():
 os.nice(15);OUT.mkdir(exist_ok=True)
 src=Q/'PAIRED_H8_R10G4_THREE_SEED_STRICT_PLACEMENT_REPORT.json';report=json.loads(src.read_text());jobs=[]
 for row in report['horizons']['8']['rows']:
  for method in ['ttc','mem0']:jobs.append(dict(method=method,case=row[method],side=row['side'],scene_seed=row['scene_seed'],model_seed=row['model_seed'],inference_seed=row['inference_seed']))
 rows=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4)as pool:
  for d in pool.map(one,jobs,chunksize=1):
   rows.append(d)
   (Q/'R13_FD_CONCORDANCE_PROGRESS.json').write_text(json.dumps({'epoch':time.time(),'completed':len(rows),'target':600,'workers':4,'mismatches':sum(not all(x.get(k,True)for k in ['success_equal','phase_equal','phase_times_equal','strict_success_equal','numeric_pass'])for x in rows),'unknown':sum(x.get('unknown',False)for x in rows)}))
 import numpy as np
 def quant(a):
  return dict(n=len(a),**{k:float(v)for k,v in zip(['p50','p95','p99'],np.percentile(a,[50,95,99]))})if a else dict(n=0,p50=None,p95=None,p99=None)
 pooled={}
 for label,subset in [('all',rows)]+[(m,[x for x in rows if x['method']==m])for m in ['ttc','mem0']]:
  pooled[label]={k:{n:quant([v for x in subset for v in x.get('noise_raw_samples',{}).get(k,{}).get(n,[])])for n in ['physx_linear','physx_angular','FD_linear','FD_angular']}for k in ['A','B']}
 for x in rows:x.pop('noise_raw_samples',None)
 out={'epoch':time.time(),'stage':'diagnostic','reference_sha256':REFSHA,'our_script_sha256':hashlib.sha256((Q/'fd_velocity_strict_v1.py').read_bytes()).hexdigest(),'source_report_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'numeric_tolerance_frozen':TOL,'noise_window':'sim_time <=1s, original-pad supported, zero robot contact, truncated at first support loss/contact; NOT certified before first robot command; no velocity filtering','noise_quantiles_pooled_raw_samples':pooled,'rows':rows,'completed':len(rows),'unknown':sum(x.get('unknown',False)for x in rows),'mismatches':[x['case_id']for x in rows if not x.get('unknown')and not all(x[k]for k in ['success_equal','phase_equal','phase_times_equal','strict_success_equal','numeric_pass'])]}
 (Q/'R13_FD_REFERENCE_CONCORDANCE_REPORT.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k not in ['rows','noise_quantiles_pooled_raw_samples']}))
if __name__=='__main__':main()
