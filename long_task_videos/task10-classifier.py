"""Task10-specific corrected release classification. Frozen R2 counts completed
objects only after weighing then own-pad return; no task7 pan-only reuse.
Original main rows compare exact frozen R2 phase/events to authoritative summary.
New #72/#75 baselines get explicitly-labelled diagnostic R2 CPU scores, preserving
producer v1.1 results and requiring full final-phase parity on v1.1 replay.
"""
from pathlib import Path
import json,sys,math,hashlib,importlib.util,concurrent.futures,time,collections,copy
W=Path(__file__).parent;ROOT=W.parent;OUT=W/'task10_scan_v2';OUT.mkdir(exist_ok=True)
BASE=Path('/project_a02012413/public/liyufeng/safelab_task10_new_variants_20261102/eval_v11_20261103')
ORACLE_SHA='2a4f3209b90822fa09da57424f13cea55cdcaa63334b7a9d42974586b4741708'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=BASE/'v13_lenient_20261106/supportproof_r2/place_v13_lenient.py';assert hashlib.sha256(p.read_bytes()).hexdigest()==ORACLE_SHA
O=load('frozen_t10_r2',p);PlaceTen=load('frozen_t10_v11',BASE/'v12_relaxed_20261105/base_place_v11.py').PlaceTen
class Shim:
 def __init__(self,profile,origin):self.inner=O.LenientObjects(profile,origin);self.origin=origin;self.supports=profile['scene']['supports'];self.xy_tolerance_m=self.inner.xy
 @property
 def done(self):return set(self.inner.completed)
 @property
 def weighed(self):return set(self.inner.weighed)
 @property
 def phase(self):return self.inner.phase
 @property
 def events(self):return self.inner.events
 def observe(self,tick,poses,contacts):return self.inner.observe({'tick':tick,'poses':poses,'contacts':contacts})
class Oracle:
 PlacementFour=Shim
 @staticmethod
 def upright(q):return 1-2*(q[1]**2+q[2]**2)/sum(x*x for x in q)
D=json.loads((W/'task10_sources.json').read_text());old={r['case_id']:r for r in json.loads((W/'TASK10_SCAN_ALL.json').read_text())};AUTH={};SCENES={};CASES=[]
contract=W/'task10_authoritative_scoring_contract.json';contract.write_text(json.dumps({'source_profile':D['profile'],'env_origins':[[0,0,0]],'provenance':'derived scoring contract: authoritative R2 profile, audited world0 cohort; not a fabricated original capture contract'}))
for x in D['rows']:
 cid=x.get('source_case_id')or x['slot_id'].replace('|','_');c=copy.deepcopy(old[cid]);v11=x.get('old_protocols',{}).get('placement-v1.1',{});r={'case_id':cid,'order':x['order'],'original_termination':x.get('terminal_failure')or('time_limit'if x.get('rows',0)>=28800 else'closed_source_result'),'historical_protocols':{'v1.1':dict(v11,verdict='U'if x.get('unknown')else'S'if v11.get('success')else'F',summary={'events':[]})},'v13':{'verdict':'U'if x.get('unknown')else'S'if x.get('success')else'F','success':None if x.get('unknown')else bool(x.get('success')),'phase':x.get('phase'),'N':5,'summary':{'events':x.get('events',[])}}}
 AUTH[cid]=r;SCENES[cid]=str(contract);c['source_authority']='authoritative task10 supportproof_r2 summary';CASES.append(c)
# Parse only the function body, under an explicit task10 adapter and invariants.
s=(W/'task7_fix_v2.py').read_text();s=s[s.index('def nearest('):s.index("if __name__=='__main__':")]
s=s.replace("'ABCD'","'ABCDE'").replace('[False]*4','[False]*5').replace('[None]*4','[None]*5').replace("==4,'successful trace incomplete'","==5,'successful trace incomplete'")
s=s.replace('set(o.done)','set(o.weighed)').replace('key in o.done','key in o.weighed')
s=s.replace("o=oracle.PlacementFour(contract['source_profile'],contract['env_origins'][0]);", "o=oracle.PlacementFour(contract['source_profile'],contract['env_origins'][0]);checker11=PlaceTen(contract['source_profile'],r['order'],contract['env_origins'][0]);")
s=s.replace("while oldj<len(events11)and events11[oldj]['tick']<=tick:oldj+=1", "prior11=checker11.phase;checker11.observe(z);oldj=checker11.phase\n  if oldj>prior11:\n   advanced_key='ABCDE'[int(r['order'][min(prior11//2,4)])-1];progress.append((tick,advanced_key,11));last_progress=max(last_progress,tick);wrong.pop(advanced_key,None)")
s=s.replace("assert h.hexdigest()==c['source_raw']['sha256'],'raw SHA mismatch'", "assert h.hexdigest()==c['source_raw']['sha256'],'raw SHA mismatch'\n assert checker11.phase==r['historical_protocols']['v1.1'].get('phase',0),'v1.1 phase mismatch source='+str(r['historical_protocols']['v1.1'].get('phase'))+' replay='+str(checker11.phase)\n r['historical_protocols']['v1.1']['summary']={'events':checker11.events}")
ns=dict(__name__='task10_corrected_features',__file__=str(Path(__file__)),W=W,ROOT=ROOT,OUT=OUT,AUTH=AUTH,SCENES=SCENES,ORACLE_SHA=ORACLE_SHA,oracle=Oracle,PlaceTen=PlaceTen)
# Modules and labels normally imported by the task7 header.
import collections as coll
from failure_rules import LABELS
ns.update(Path=Path,json=json,hashlib=hashlib,math=math,collections=coll,time=time,LABELS=LABELS)
exec(compile(s,'task10_corrected_features','exec'),ns);core=ns['fix']
def one(c):return core(c)
def baseline(r):
 cid=r['case_id'];out=ROOT/'task10_baseline_inputs'/cid;ref=json.loads((out/'EXTRACT_RECEIPT.json').read_text());scene=json.loads((out/'SCENE_CONTRACT.json').read_text());raw=out/'physical_120hz.jsonl';o=O.LenientObjects(scene['source_profile'],scene['env_origins'][0]);h=hashlib.sha256()
 for b in raw.open('rb'):h.update(b);o.observe(json.loads(b))
 assert h.hexdigest()==r['raw_sha256'];v11=r['protocols']['v11'];AUTH[cid]={'case_id':cid,'order':r['case']['order'],'original_termination':r['original_result']['status'],'historical_protocols':{'v1.1':dict(v11,verdict='S'if v11['success']else'F',summary={'events':[]})},'v13':{'verdict':'S'if o.final_ok else'F','success':o.final_ok,'phase':o.phase,'N':5,'summary':{'events':o.events}}};SCENES[cid]=str(out/'SCENE_CONTRACT.json');frame0=json.loads(next((out/'frames.jsonl').open()))['native_tick'];c={'task':10,'method':'pi05_40k'if r['record'].startswith('pi05')else'memoryvla_30k','horizon':r['case']['execution_horizon'],'checkpoint':r['case']['checkpoint_step'],'case_id':cid,'scene_index':r['case']['scene_index'],'seed':r['case']['seed'],'reason':'other','source_raw':{'file':str(raw),'sha256':r['raw_sha256'],'rows':r['rows']},'source_video':str(out/'chest.mp4'),'source_video_exists':True,'video_origin_tick':frame0,'raw_origin_tick':r['first_tick'],'outcomes':{'v1.1':AUTH[cid]['historical_protocols']['v1.1'],'v1.3':AUTH[cid]['v13']},'source_archive':r['archive'],'source_authority':'v1.1 producer result; v1.3 new diagnostic frozen-R2 CPU rescore, no formal admission promotion','selection':[]}
 result=core(c);result['v11_total']=10;result['v13_total']=5;return result
if __name__=='__main__':
 kind=sys.argv[1]if len(sys.argv)>1 else'main';inputs=CASES if kind=='main'else json.loads((W/'task10_baseline_sources.json').read_text())['cases'];worker=one if kind=='main'else baseline;res=[];err=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4)as pool:
  fs={pool.submit(worker,c):c for c in inputs}
  for f in concurrent.futures.as_completed(fs):
   try:res.append(f.result())
   except Exception as e:err.append({'case':fs[f].get('case_id'),'error':str(e)})
   (W/('TASK10_FIXED_'+kind.upper()+'_STATE.json')).write_text(json.dumps({'closed':len(res),'expected':len(inputs),'errors':err,'epoch':time.time()}))
 assert not err,err[:5]
 (W/('TASK10_FIXED_'+kind.upper()+'.json')).write_text(json.dumps(res,separators=(',',':')));print(json.dumps({'closed':len(res),'counts':{str(k):dict(collections.Counter(r['reason']for r in res if(r['method'],r['horizon'])==k))for k in sorted(set((r['method'],r['horizon'])for r in res))}}),flush=True)
