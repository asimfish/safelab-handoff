"""Frozen-protocol result tables; retains all planned denominators and censoring."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,math,re,time
import numpy as np
S=Path('/project_a02012413/public/liyufeng/safelab_mem0_7weigh_eval_20261027');R=S/'inference_1400_cpu_20261106';V=S/'eval_v13_lenient_cpu_20261106/support_contact_authoritative_v2'
def ref(p):return dict(file=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def wilson(s,n):
 z=1.959963984540054;p=s/n;den=1+z*z/n;c=(p+z*z/(2*n))/den;rad=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den;return [c-rad,c+rad]
def normalize(v,N):
 if v is None:return dict(verdict='U',phase=None,N=N,per_k={str(k):'U'for k in range(1,N+1)})
 p=v.get('phase');verdict=v['verdict'];per=v.get('per_k',{str(k):'S'if p is not None and p>=k else'F'if verdict=='F'else'U'for k in range(1,N+1)})
 return dict(verdict=verdict,phase=p,N=N,per_k=per)
def canonical(row):
 m=re.search(r'v180_o(1234|4321)_r(\d{3})(?:$|_)',row['case_id']);assert m,row['case_id'];order,n=m.group(1),int(m.group(2));assert order==row['order']and 0<=n<50
 return 'v180_o'+order+'_r'+str(n).zfill(3)
def summarize(cases,protocol,N):
 vals=[r['scores'][protocol]for r in cases];success=sum(v['verdict']=='S'for v in vals);unknown=sum(v['verdict']=='U'for v in vals);valid=[v['phase']for v in vals if v['verdict']!='U'];n=len(cases);hist=Counter(str(v)for v in valid);assert sum(hist.values())==n-unknown
 mean=float(np.mean(valid))if valid else None
 rng=np.random.default_rng(20261106);means=[]
 groups=[[r['scores'][protocol]['phase']for r in cases if r['order']==o and r['scores'][protocol]['verdict']!='U']for o in ['1234','4321']]
 if valid:
  draws=[rng.choice(g,(10000,len(g)))for g in groups if g];means=np.concatenate(draws,axis=1).mean(axis=1);mean_CI=np.quantile(means,[.025,.975]).tolist()
 else:mean_CI=None
 split={}
 for o in ['1234','4321']:
  rows=[r['scores'][protocol]for r in cases if r['order']==o];known=[r['phase']for r in rows if r['verdict']!='U'];split[o]=dict(trials=len(rows),success=sum(r['verdict']=='S'for r in rows),unknown=sum(r['verdict']=='U'for r in rows),mean_phase=float(np.mean(known))if known else None)
 per={str(k):dict(success=sum(v['per_k'][str(k)]=='S'for v in vals),unknown=sum(v['per_k'][str(k)]=='U'for v in vals),trials=n)for k in range(1,N+1)}
 return dict(trials=n,success=success,unknown=unknown,failure=n-success-unknown,Wilson95=wilson(success,n),N=N,half_k=math.ceil(N/2),half_task=per[str(math.ceil(N/2))],mean_phase=mean,mean_phase_bootstrap95=mean_CI,phase_hist=dict(hist),SR_at_k=per,lr_split=split,bootstrap_repetitions=10000,unknowns_remain_in_rate_denominator=True,mean_and_hist_exclude_unknown=True)
def main():
 oldfile=V/'MAIN_COMPLETE.json';newfile=R/'new_raw_rescore/COMPLETE.json';old=json.loads(oldfile.read_text());new=json.loads(newfile.read_text());assert new['raw_verified']==499 and len(new['rows'])==499
 merged=[]
 for x in old['rows']:
  if x['kind']!='main':continue
  hist=x.get('historical_protocols',{});scores={p:normalize(hist.get(k),7)for p,k in [('strict','strict'),('v1.1','v1.1'),('v1.2','v1.2-relaxed')]};scores['v1.3']=normalize(x.get('v13'),4)
  merged.append(dict(case_id=x['case_id'],variant=x['variant'],horizon=x['horizon'],seed_index=0,seed=x.get('seed'),order=x['order'],scenario_id=canonical(x),scores=scores,raw_SHA_verified=x['raw_SHA_verified'],ever_infra_unknown=None,source='historical_seed0'))
 assert len(merged)==200
 source=json.loads((R/'sdk_ledger_review/ROOT_SDK_CLOSURES.json').read_text());packages={r['package']:r for r in source['rows']};flags={}
 for name,p in packages.items():
  q=Path(p['source_state']['file']);assert ref(q)['sha256']==p['source_state']['sha256'];d=json.loads(q.read_text())['runtime']['paper_case_ledger'];flags.update({cid:bool(row['ever_unknown'])for cid,row in d['cases'].items()})
 for x in new['rows']:
  assert x['raw_SHA_verified']and x['v11_matches_original_SDK'];scores={p:normalize(v,4 if p=='v1.3'else 7)for p,v in x['protocols'].items()};strict=x['source_strict'];scores['strict']=normalize(dict(verdict='U'if strict.get('censored')else'S'if strict['success']else'F',phase=strict['phase']),7)
  merged.append(dict(case_id=x['case_id'],variant=x['variant'],horizon=x['horizon'],seed_index=x['seed_index'],seed=x['seed'],order=x['order'],scenario_id=x['scenario_id'],scores=scores,raw_SHA_verified=True,ever_infra_unknown=flags[x['case_id']],source='new_full_raw'))
 # Insert explicitly missing planned case, rather than losing it from denominator.
 A=S/'acceleration_24gpu_20261106';index=json.loads((A/'ACTIVE_AFTER_RESUME96_MANIFESTFIX.json').read_text());known={x['case_id']for x in merged}
 for row in index['prepared']:
  if row['cases']!=100:continue
  w=json.loads((A/'packages'/row['name']/'source/WORKLIST.json').read_text())
  for c in w['cases']:
   if c['id']in known:continue
   merged.append(dict(case_id=c['id'],variant=c['variant'],horizon=c['horizon'],seed_index=c['seed_index'],seed=c['seed'],order=c['order'],scenario_id=c['scenario_id'],scores={p:normalize(None,N)for p,N in [('strict',7),('v1.1',7),('v1.2',7),('v1.3',4)]},raw_SHA_verified=False,ever_infra_unknown=flags[c['id']],source='exhausted_unknown_no_valid_raw'))
 assert len(merged)==700 and len({x['case_id']for x in merged})==700
 rows=[];by=defaultdict(list)
 for c in merged:by[(c['variant'],c['horizon'],c['seed_index'])].append(c)
 for key,cases in sorted(by.items()):
  assert len(cases)==100 and len({r['scenario_id']for r in cases})==100
  row=dict(variant=key[0],horizon=key[1],seed_index=key[2],scores={p:summarize(cases,p,N)for p,N in [('strict',7),('v1.1',7),('v1.2',7),('v1.3',4)]},raw_SHA_verified=sum(r['raw_SHA_verified']for r in cases))
  if key[2]>0 or key[1]==4:
   row['ever_unknown_sensitivity']={p:dict(success=sum(r['scores'][p]['verdict']=='S'and not r['ever_infra_unknown']for r in cases),trials=100,rule='any infrastructure unknown attempt counts as failure')for p in ['v1.1','v1.2','v1.3']}
  else:row['ever_unknown_sensitivity']=None
  rows.append(row)
 # Paired hierarchical bootstrap: resample inference seeds and paired scene IDs.
 table={(r['variant'],r['seed_index'],r['scenario_id']):r for r in merged if r['horizon']==8};scene_ids=sorted({r['scenario_id']for r in merged});assert len(scene_ids)==100
 paired={};totals=[]
 for p,N in [('strict',7),('v1.1',7),('v1.2',7),('v1.3',4)]:
  matrices={metric:np.full((3,100),np.nan)for metric in ['success','phase']};missing=0
  for seed in range(3):
   for j,scene in enumerate(scene_ids):
    t=table[('ours_aligned_30k',seed,scene)]['scores'][p];m=table[('mem0_30k',seed,scene)]['scores'][p]
    if t['verdict']=='U'or m['verdict']=='U':missing+=1;continue
    matrices['success'][seed,j]=float(t['verdict']=='S')-float(m['verdict']=='S');matrices['phase'][seed,j]=t['phase']-m['phase']
  vals={};rng=np.random.default_rng(20261106)
  for metric,mat in matrices.items():
   samples=[]
   for _ in range(10):
    seeds=rng.integers(0,3,(1000,3));indices=np.concatenate([rng.integers(0,50,(1000,50)),rng.integers(50,100,(1000,50))],axis=1);d=mat[seeds[:,:,None],indices[:,None,:]];v=np.nanmean(d,axis=(1,2));samples.extend(v.tolist())
   vals[metric]=dict(TTC_minus_Mem0=float(np.nanmean(mat)),bootstrap95=np.nanquantile(samples,[.025,.975]).tolist(),known_pairs=int(np.isfinite(mat).sum()),planned_pairs=300,unknown_pairs=missing)
  paired[p]=dict(**vals,bootstrap='10000 hierarchical paired resamples:3 inference seeds then common paired scene IDs stratified50/50 order; only closed known-pair contrasts, full denominators retained separately')
  for variant in ['mem0_30k','ours_aligned_30k']:
   cs=[r for r in merged if r['horizon']==8 and r['variant']==variant];totals.append(dict(variant=variant,horizon=8,seeds=[0,1,2],protocol=p,progress='3/5 requested inference seeds complete',**summarize(cs,p,N)))
 result=dict(schema='task7_original_three_seed_h8_and_h4_cpu_results.v1',epoch=time.time(),stage='diagnostic',source_main_results_unchanged=True,scene_list_sha256='f6d728df04ff3d87927700173aa7f83c5ffa5de699d750f6da819e97156fae6f',training_resize=True,execution_chain='A739/world0/K-cubic',topology='N1x4 independent-process per GPU',raw_verified=698,planned=700,rows=rows,three_seed_totals=totals,paired=paired,cases=merged,source_refs=[ref(oldfile),ref(newfile),ref(R/'sdk_ledger_review/ROOT_SDK_CLOSURES.json')],entry=ref(Path(__file__)),scope_limits=['Three completed inference seeds, not all five yet','strict and FD outcomes censored by placement early stop remain unknown; task7 strict has no velocity predicate so FD identity','v1.3 counts4 distinct cups on weighing pan; v1.1/v1.2 count7 ordered stages','No source positions jittered; two training physical layouts repeated across canonical100 scene IDs','Historical seed0 ever-unknown sensitivity unavailable in this aggregation; not guessed zero'])
 out=R/'THREE_SEED_RESULTS.json';out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(file=ref(out),rows=rows,three_seed_totals=totals,paired=paired)))
if __name__=='__main__':main()
