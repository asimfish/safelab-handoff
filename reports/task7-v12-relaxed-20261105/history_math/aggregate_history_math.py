"""Read exact small historical CPU receipts; never open raw or promote contact math."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,hashlib,json,re,time,math

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
def checkpoint(variant):
 m=re.search(r'(?:^|_)(20|30)k(?:_|$)',variant);assert m,variant;return int(m[1])*1000

def project(index,index_file):
 assert index['expected']==len(index['records'])==index['cached']
 assert not index.get('pending_readbacks')
 out=[];seen=set();receipt_bytes=0;index_sha=sha(index_file)
 for item in index['records']:
  p=Path(item['receipt']['file']);b=p.read_bytes();assert len(b)<=1<<20 and hashlib.sha256(b).hexdigest()==item['receipt']['sha256'];source=json.loads(b);receipt_bytes+=len(b)
  key=(source['variant'],source['horizon'],source['condition'],source['case_id']);assert key not in seen;seen.add(key)
  for k in ['case_id','variant','horizon','condition']:assert source[k]==item[k]
  assert source['formal_placement_success']is None and source['complete_all_Robot_contact_coverage_qualified']is False
  assert source['canonical_verdicts']==item['canonical_verdicts']=={'v1.1':'U','v1.2-relaxed':'U'}
  assert source['original_stop_extended']is False and source['NN_Kit_GPU_API_calls']==0
  assert source['math_protocols']==item['math_protocols'] and source['strict_original']==item['strict_original']
  assert source['strict_original']['strict_reexecuted']is False
  available=source.get('raw_SHA_verified')is True;raw=source.get('raw');assert bool(raw)==available
  if available:assert len(raw['sha256'])==64 and isinstance(raw['bytes'],int)
  o={}
  for name in ['v1.1','v1.2-relaxed']:
   x=source['math_protocols'][name];status=x['verdict'];phase=x['phase'];assert status in ['S','F','U'];assert x['success']==({'S':True,'F':False,'U':None}[status]);assert phase is None or type(phase)is int and 0<=phase<=7
   if not available:assert status=='U'and phase is None
   o[name]={'verdict':status,'success':x['success'],'phase':phase if status!='U'else None,'observed_phase_lower_bound':phase,'censored':x.get('censored',False),'per_k':{str(k):'S'if phase is not None and phase>=k else'F'if status=='F'else'U'for k in range(1,8)},'fall_after_place_objects':x.get('summary',{}).get('fall_after_place',0)}
  out.append({'case_id':source['case_id'],'variant':source['variant'],'checkpoint':checkpoint(source['variant']),'horizon':source['horizon'],'condition':source['condition'],'order':source.get('order'),'seed':source.get('seed'),'classification':'diagnostic_historical_contact_math_only','raw_SHA_verified':available,'raw':{k:raw[k]for k in ['file','bytes','sha256']}if raw else None,'canonical_verdicts':source['canonical_verdicts'],'formal_placement_success':None,'strict_original':source['strict_original'],'math_protocols':o,'source_contract_evidence':{k:source.get(k)for k in ['source_manifest_sha256','original_input_manifest_sha256','canonical_audit_sha256','condition_version','execution_chain','preprocess_resize','training_resize','completionfix']},'execution_chain_scope':'P1 original smoke chain'if source['condition']=='historical_P1_smoke20'else'Original historical condition; exact chain/version not independently resolved by this aggregation','training_resize_actual':None,'training_resize_actual_status':'unknown; not inferred from variant name','source_receipt':dict(item['receipt']),'source_index_sha256':index_sha})
 return out,receipt_bytes

def wilson(s,n):
 z=1.959963984540054;p=s/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return {'low':max(0,c-h),'high':min(1,c+h),'confidence':.95}

def counts(statuses,n):
 c=Counter(statuses);assert sum(c.values())==n and set(c)<=set('SFU')
 return {'S':c['S'],'F':c['F'],'U':c['U'],'N':n,'valid_n':c['S']+c['F'],'confirmed_success_fraction_full_n':c['S']/n,'complete_verdict_SR':c['S']/n if not c['U']else None,'SR_identification_bounds':[c['S']/n,(c['S']+c['U'])/n],'Wilson95_confirmed_success_full_n':wilson(c['S'],n),'metric_role':'contact-math-only confirmed-success indicator; not canonical placement SR'}

def aggregate(rows):
 groups=defaultdict(list)
 for r in rows:groups[(r['variant'],r['checkpoint'],r['horizon'],r['condition'])].append(r)
 out=[]
 for (v,ckpt,h,condition),rr in sorted(groups.items()):
  n=len(rr);g={'variant':v,'checkpoint':ckpt,'horizon':h,'condition':condition,'n_actual_historical_cases':n,'raw_full_SHA_CPU_verified_n':sum(r['raw_SHA_verified']for r in rr),'raw_missing_n':sum(not r['raw_SHA_verified']for r in rr),'formal_placement_success':None,'canonical_placement_v11':{'S':0,'F':0,'U':n},'canonical_placement_relaxed':{'S':0,'F':0,'U':n},'math':{}}
  g['execution_and_preprocess_evidence']={'execution_scope':'P1 original smoke chain'if condition=='historical_P1_smoke20'else'Original historical condition; exact chain/version unresolved','condition_version':None,'training_resize_actual':None,'completionfix_actual':None,'original_variant_name_preserved':True,'source_manifest_sha256s':sorted({r['source_contract_evidence']['source_manifest_sha256']for r in rr if r.get('source_contract_evidence',{}).get('source_manifest_sha256')}),'limitation':'No chain, training-resize, Gen/classifier or completionfix flag inferred from method name. Exact source contract references retained per case.'}
  strict=[r['strict_original']for r in rr];g['strict_original_history_only']=counts(['U'if x['success']is None else'S'if x['success']else'F'for x in strict],n);g['strict_original_history_only']['new_full_strict_reexecution']=False
  for name in ['v1.1','v1.2-relaxed']:
   os=[r['math_protocols'][name]for r in rr];known=[x['phase']for x in os if x['verdict']!='U'];observed=[x['observed_phase_lower_bound']for x in os if x['observed_phase_lower_bound']is not None]
   z=counts([x['verdict']for x in os],n);z.update({'mean_phase_valid_closed_only':sum(known)/len(known)if known else None,'mean_phase_n':len(known),'phase_hist_valid_closed_only':dict(sorted(Counter(known).items())),'observed_phase_lower_bound_mean':sum(observed)/len(observed)if observed else None,'observed_phase_known_n':len(observed),'observed_phase_lower_bound_hist':dict(sorted(Counter(observed).items())),'per_stage':{str(k):counts([x['per_k'][str(k)]for x in os],n)for k in range(1,8)},'fall_after_place_objects':sum(x['fall_after_place_objects']for x in os),'censored_n':sum(x['censored']for x in os)})
   g['math'][name]=z
  out.append(g)
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-index',type=Path,required=True);p.add_argument('--source-sha256',required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();assert sha(a.source_index)==a.source_sha256;assert not a.output_dir.exists();a.output_dir.mkdir();index=load(a.source_index);rows,receipt_bytes=project(index,a.source_index);groups=aggregate(rows);parts=[]
 for i in range(0,len(rows),50):
  f=a.output_dir/f'cases-part{i//50:02}.json';dump(f,{'schema':'task7_historical_contact_math_projection.v1','source_index_sha256':a.source_sha256,'rows':rows[i:i+50]});assert f.stat().st_size<200000;parts.append({'file':f.name,'bytes':f.stat().st_size,'sha256':sha(f),'rows':len(rows[i:i+50])})
 report={'schema':'task7_historical_contact_math_aggregate.v1','epoch':time.time(),'stage':'diagnostic','metric_role':'historical_contact_math_appendix','formal_admission_granted':False,'source_index':{'file':str(a.source_index),'bytes':a.source_index.stat().st_size,'sha256':a.source_sha256},'source_final':index.get('source_final'),'source_receipts_full_SHA_verified_n':len(rows),'source_receipt_bytes_read':receipt_bytes,'raw_full_SHA_CPU_verified_n':sum(r['raw_SHA_verified']for r in rows),'source_worker_raw_bytes_verified':sum(r['raw']['bytes']for r in rows if r['raw']),'new_raw_NN_GPU_API_reads_or_calls':0,'actual_historical_n':len(rows),'canonical_v11_U':len(rows),'canonical_relaxed_U':len(rows),'strict_original_reexecuted':False,'groups':groups,'parts':parts,'aggregation_source_sha256':sha(__file__),'boundaries':['All robot-contact coverage remains unqualified; all canonical v1.1 and relaxed verdicts U, formal_placement_success null.','Math S/F/U is conditional on incomplete historical contact data; never substitute it into the two main rescores or formal12 cells.','Strict original is historical source RESULT/phase binding, not a newly completed strict oracle replay.','Denominator is only the frozen actual historical case inventory, never unrun planned100 rows. Missing raw is U; censored observed prefixes retained per-stage.','Old P1 uses seed889 and its original preprocessing/execution chain, unlike mainA739K; no cross-cohort causal comparison.']};dump(a.output_dir/'summary.json',report);print(json.dumps({'output':str(a.output_dir),'summary_sha256':sha(a.output_dir/'summary.json'),'n':len(rows),'raw_n':report['raw_full_SHA_CPU_verified_n'],'parts':len(parts)}))
