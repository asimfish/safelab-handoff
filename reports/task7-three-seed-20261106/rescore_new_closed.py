"""Download exact own-prefix traces and CPU-score frozen protocols. STS is stdin only."""
from pathlib import Path
import concurrent.futures,hashlib,json,os,sys,time,traceback
S=Path('/project_a02012413/public/liyufeng/safelab_mem0_7weigh_eval_20261027')
B=Path('/projects/a02012413/buckets/zenith-a02012413/liyufeng/safelab_mem0_7weigh_eval_20261027')
O=S/'inference_1400_cpu_20261106/new_raw_rescore'
V=S/'eval_v13_lenient_cpu_20261106/support_contact_authoritative_v2'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def dump(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);q=p.with_name(p.name+f'.{os.getpid()}.pending');q.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n');q.replace(p)
def ref(p):return dict(file=str(p),sha256=sha(p),bytes=p.stat().st_size)
STORE=None
def download(item):
 key=item['source_write_prefix']+'artifacts/'+item['case_artifact_dir']+'/'+item['case_id']+'/physical_120hz.jsonl'
 assert key.startswith('liyufeng/safelab_mem0_7weigh_eval_20261027/new_dense_workpackages/')
 p=B/'inference_1400_cpu_20261106/raw_traces'/item['variant']/(str(item['horizon'])+'_'+str(item['seed_index']))/(item['physical_trace_sha256']+'.jsonl')
 if p.exists():
  assert p.is_file()and not p.is_symlink()and sha(p)==item['physical_trace_sha256'];return p,key
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+f'.{os.getpid()}.download.pending')
 c,r=STORE._request('GET',key)
 try:
  size=r.getheader('Content-Length');size=None if size is None else int(size);assert size is None or 0<size<=256<<20
  h=hashlib.sha256();n=0
  with tmp.open('xb')as f:
   while True:
    b=r.read(1<<20)
    if not b:break
    n+=len(b);assert n<=256<<20;h.update(b);f.write(b)
   f.flush();os.fsync(f.fileno())
  assert n and (size is None or size==n)and h.hexdigest()==item['physical_trace_sha256'];tmp.rename(p)
 finally:
  c.close()
  if tmp.exists():tmp.unlink()
 assert sha(p)==item['physical_trace_sha256'];return p,key
def verdict(summary,status,N):
 phase=summary['completed_phases'];s=bool(summary['success']);closed_failure=status in ('time_limit','physical_failure','object_fell','object_toppled')
 v='S'if s else'F'if closed_failure else'U'
 return dict(verdict=v,success=True if v=='S'else False if v=='F'else None,phase=phase,N=N,per_k={str(k):'S'if phase>=k else'F'if v=='F'else'U'for k in range(1,N+1)},summary=summary)
def one(item):
 from oracle_v13 import PlacementFour
 from oracle_relaxed_reference import PlacementSeven
 out=O/'cases'/(item['case_id']+'.json')
 if out.exists():return json.loads(out.read_text())
 r=dict(case_id=item['case_id'],variant=item['variant'],horizon=item['horizon'],seed_index=item['seed_index'],seed=item['seed'],scenario_id=item['scenario_id'],order=item['order'],original_SDK_closure=item['closure'],raw_SHA_verified=False,stage='diagnostic')
 try:
  p=None;last=None
  for attempt in range(3):
   try:p,key=download(item);break
   except Exception as e:
    last=type(e).__name__
    if attempt<2:time.sleep(2**attempt)
  if p is None:raise RuntimeError('raw_download_'+str(last))
  cr=Path(item['closure']['file']);assert sha(cr)==item['closure']['sha256'];closure=json.loads(cr.read_text());case=cr.parent.with_name(cr.parent.name[:-8]);scene=case/'SCENE_CONTRACT.json';sd=json.loads(scene.read_text());origin=sd['env_origins'][0];profile=sd['source_profile'];status=closure['status']
  v11=PlacementSeven(profile,item['order'],origin,protocol='SafeLab-Eval-v1.1');v12=PlacementSeven(profile,item['order'],origin);v13=PlacementFour(profile,origin)
  count=0;first=None;h=hashlib.sha256()
  for raw in p.open('rb'):
   h.update(raw);z=json.loads(raw);count+=1
   assert z.get('contact_sample_observed')is True and z.get('all_Robot_contact_reporting_contract_verified')is True
   if first is None:first=z['tick'];assert first==125
   assert z['tick']==124+count
   v11.observe(z['tick'],z['poses'],z['contacts']);v12.observe(z['tick'],z['poses'],z['contacts']);v13.observe(z['tick'],z['poses'],z['contacts'])
  assert count==item['physics_rows']and z['tick']==item['last_tick']and h.hexdigest()==item['physical_trace_sha256']
  summary=v11.finish();expected=item['scores']['placement'];assert summary['success']==expected['success']and summary['completed_phases']==expected['phase'],'offline_v11_disagrees_with_original_SDK'
  r.update(raw_SHA_verified=True,raw={**ref(p),'object_key':key,'rows':count},scene=ref(scene),status=status,protocols={'v1.1':verdict(summary,status,7),'v1.2':verdict(v12.finish(),status,7),'v1.3':verdict(v13.finish(),status,4)},source_strict=item['scores']['strict'],source_FD=item['scores']['FD'],v11_matches_original_SDK=True,raw_future_beyond_original_termination_inferred=False)
 except Exception as e:
  r.update(error_type=type(e).__name__,error_code=str(e)[:120]if isinstance(e,(RuntimeError,AssertionError))else type(e).__name__,protocols={p:dict(verdict='U',success=None,phase=None,N=N,per_k={str(k):'U'for k in range(1,N+1)})for p,N in [('v1.1',7),('v1.2',7),('v1.3',4)]})
 dump(out,r);return r
def main():
 global STORE
 x=json.load(sys.stdin);grant=x.pop('grant');assert not x
 O.mkdir(parents=True,exist_ok=True);sys.path[:0]=[str(V),str(S/'acceleration_24gpu_20261106/packages/mem0_h8_seed1_20261106v1_retry1/source')]
 assert sha(V/'oracle_v13.py')=='84da94e16d3290b869ef2f713dbdab96bc00169f682a33a4f0fa65502179080d'
 assert sha(V/'oracle_relaxed_reference.py')=='ead111d6deac265578f9015c65ef8f8b371127583fb2f9f0ccdc0a2c7339c674'
 from bos_https import BosHTTPS
 STORE=BosHTTPS(grant,read_prefixes=['liyufeng/safelab_mem0_7weigh_eval_20261027/new_dense_workpackages/'],write_prefix='liyufeng/safelab_mem0_7weigh_eval_20261027/inference_1400_cpu_20261106/',timeout=90);grant=None
 source=S/'inference_1400_cpu_20261106/sdk_ledger_review/ROOT_SDK_CLOSURES.json';manifest=json.loads(source.read_text());tasks=manifest['cases'];assert len(tasks)==499
 started=time.time();rows=[]
 # Inherited in-memory STS only; no credentials in source, argv, disk, or results.
 with concurrent.futures.ProcessPoolExecutor(max_workers=2)as pool:
  futures=[pool.submit(one,t)for t in tasks]
  for f in concurrent.futures.as_completed(futures):
   rows.append(f.result());dump(O/'PROGRESS.json',dict(epoch=time.time(),closed=len(rows),planned=len(tasks),raw_verified=sum(r['raw_SHA_verified']for r in rows),error_counts={str(k):sum(r.get('error_type')==k for r in rows)for k in set(r.get('error_type')for r in rows)if k is not None},wall_seconds=time.time()-started))
 rows.sort(key=lambda r:r['case_id']);dump(O/'COMPLETE.json',dict(schema='task7_new499_full_raw_three_protocol_cpu.v1',rows=rows,planned=len(tasks),raw_verified=sum(r['raw_SHA_verified']for r in rows),source_manifest=ref(source),oracle_v13=ref(V/'oracle_v13.py'),oracle_v12_v11=ref(V/'oracle_relaxed_reference.py'),entry=ref(Path(__file__)),wall_seconds=time.time()-started,new_GPU_jobs=0))
 STORE.credentials.clear();STORE=None;print(json.dumps(dict(complete=True,n=len(rows),verified=sum(r['raw_SHA_verified']for r in rows))))
if __name__=='__main__':
 try:main()
 except Exception as e:
  O.mkdir(parents=True,exist_ok=True);dump(O/'ERROR.json',dict(type=type(e).__name__,error_code='CPU_worker_failed_no_credentials_recorded'));raise SystemExit(1)
