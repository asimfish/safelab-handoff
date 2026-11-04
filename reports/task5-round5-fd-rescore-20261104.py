"""CPU-only three-oracle rescore of verified owned archives; no trace files written.

Archive bytes stay bounded in RAM, signed URLs stay in RAM, and all saved output
is small metadata. FD uses common math and actual recorded clocks. Task5's
strict oracle has no velocity predicate, so replacing velocity cannot change
the predicate; clock validity is nevertheless required independently for FD.
"""
import argparse,collections,gzip,hashlib,importlib.util,io,json,pathlib,sys,tarfile,time,urllib.request,urllib.parse
sys.path.append('/usr/lib/python3/dist-packages')
import numpy as np
F=pathlib.Path(__file__).resolve().parent;Q=F.parents[1]
sys.path.insert(0,str(Q));from global12 import m
import persistent_transport;persistent_transport.install(m.dt)
COMMON=F/'common_FD/fd_velocity_strict_v1.py'
assert hashlib.sha256(COMMON.read_bytes()).hexdigest()=='a08ee1cd5722ea49f49147a03bc24a1594bbd65f068d1b5fc03092637a21b0d0'
sp=importlib.util.spec_from_file_location('common_fd',COMMON);common=importlib.util.module_from_spec(sp);sp.loader.exec_module(common)
ORACLES=F/'common_FD/task5_oracles'
EXPECTED={'obstruction_outcome.py':'ab916d46da2733765f9e093f847b6ad8904729c5459896995c07b3810082d712','placement_five_v11_stream.py':'ff6412d8e5af709c13a695c64a65a4846191d95ae3351ac341c188e94c522769','placement_five_v11.py':'b23aa3df68b91e06aadf0af685161b5189200c4fdddd6fad248cb98867dd679b'}
for name,sha in EXPECTED.items():assert hashlib.sha256((ORACLES/name).read_bytes()).hexdigest()==sha
sys.path.insert(0,str(ORACLES))
from obstruction_outcome import ObstructionFive
from placement_five_v11_stream import PlacementFive
PREFIX='liyufeng/safelab_task5_round5_portable_20261104/archives/'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):return None
OP=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
def save(v):
 p=F/'NEW_ARCHIVE_THREE_METRICS_v2.json';t=p.with_suffix('.pending');t.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');t.replace(p)
def payload(tar,manifest,name,limit):
 entry=tar.getmember(name);assert entry.isfile()and not entry.issym()and entry.size<=limit
 expected=manifest[name];assert expected['bytes']==entry.size
 data=tar.extractfile(entry).read(limit+1);assert len(data)==entry.size and hashlib.sha256(data).hexdigest()==expected['sha256']
 return data
def evaluate(data,cid,receipt):
 assert len(data)==receipt['bytes']and hashlib.sha256(data).hexdigest()==receipt['sha256']
 with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz')as tar:
  members=tar.getmembers();assert len(members)<10000
  seen=set()
  for member in members:
   p=pathlib.PurePosixPath(member.name)
   assert p.parts and p.parts[0]==cid and not p.is_absolute()and '..'not in p.parts and member.name not in seen and member.isfile()
   assert member.size<=128*(1<<20);seen.add(member.name)
  mf=tar.extractfile(cid+'/__archive_manifest__.json').read(4*(1<<20)+1);assert len(mf)<=4*(1<<20)
  source=json.loads(mf);assert source['case_id']==cid
  manifest={r['member']:r for r in source['files']};assert len(manifest)==len(source['files'])
  scene=json.loads(payload(tar,manifest,cid+'/SCENE_CONTRACT.json',4<<20))
  outcome=json.loads(payload(tar,manifest,cid+'/'+cid+'/RESULT.json',1<<20))
  audit=json.loads(payload(tar,manifest,cid+'/'+cid+'/INDEPENDENT_AUDIT.json',2<<20))
  strict_saved=json.loads(payload(tar,manifest,cid+'/'+cid+'/STRICT_V1_RESULT.json',1<<20))
  gz=payload(tar,manifest,cid+'/'+cid+'/physical_120hz.jsonl.gz',64<<20)
  strict=ObstructionFive(scene['source_profile'],outcome['layout'],scene['env_origins'][0]);placement=PlacementFive(scene['source_profile'],outcome['layout'],scene['env_origins'][0]);fd_strict=ObstructionFive(scene['source_profile'],outcome['layout'],scene['env_origins'][0])
  h=hashlib.sha256();count=0;first=None;last=None;fd_error=None;previous=None;previous_raw=None;fd_samples=0;maximum_speed=0.;size=0;fd_observe_calls=0
  with gzip.GzipFile(fileobj=io.BytesIO(gz))as stream:
   for raw in stream:
    count+=1;size+=len(raw);assert count<=28800 and size<=128*(1<<20)and len(raw)<=1<<20
    h.update(raw);r=json.loads(raw);assert r['tick']==scene['reference_tick']+count
    poses=np.asarray(r['poses'],dtype=np.float32);assert poses.shape==(3,7)
    strict.observe(r['tick'],poses,r['contacts']);placement.observe(r['tick'],poses,r['contacts'])
    assert r['physical_phase']==placement.phase
    if fd_error is None:
     try:
      adapted={'tick':r['tick'],'t_sim':r['t_sim'],'objects':{k:{'link_position_world_m':r['poses'][i][:3],'quaternion_world_wxyz':r['poses'][i][3:7]}for i,k in enumerate('ABC')}}
      if previous is not None:
       velocity=common.fd_pair(previous,adapted,time_key='t_sim');fd_samples+=1 if count>2 else 2
       maximum_speed=max(maximum_speed,max(float(np.linalg.norm(x['angular_velocity_rad_s']))for x in velocity.values()))
       # Run a separate frozen strict instance only after adjacent-clock/FD
       # validation. Its signature has no velocity input; this fact is explicit,
       # rather than copying the other strict instance's counters.
       if count==2:
        fd_strict.observe(previous_raw['tick'],np.asarray(previous_raw['poses'],dtype=np.float32),previous_raw['contacts']);fd_observe_calls+=1
       fd_strict.observe(r['tick'],poses,r['contacts']);fd_observe_calls+=1
      previous=adapted
      previous_raw=r
      if first is None:first=float(r['t_sim'])
      last=float(r['t_sim'])
     except (KeyError,common.UnknownTrace)as e:fd_error='missing_actual_clock'if isinstance(e,KeyError)else str(e)
  assert audit['passed']and count==audit['physics_ticks']and h.hexdigest()==audit['physics_sha256']
  strict_result={'success':strict.phase==5 and strict.failure is None,'physical_phase':strict.phase,'failure_reason':strict.failure,'unknown':False}
  placement_result={'success':placement.phase==5 and placement.failure is None,'physical_phase':placement.phase,'failure_reason':placement.failure,'unknown':False}
  assert strict_result['success']==strict_saved['success']and strict.phase==strict_saved['physical_phases']
  assert placement_result['success']==outcome['success']and placement.phase==outcome['physical_phases']and placement.events==outcome['physical_events']
  if count<2:fd_error='two_adjacent_physical_samples_required'
  if not fd_error:assert fd_observe_calls==fd_samples==count
  fd_result=({'success':None,'physical_phase':None,'unknown':True,'unknown_reason':fd_error}if fd_error else{'success':fd_strict.phase==5 and fd_strict.failure is None,'physical_phase':fd_strict.phase,'failure_reason':fd_strict.failure,'unknown':False,'velocity_source':'common FD / recorded actual t_sim','FD_physical_samples':fd_samples,'FD_predicate_observe_calls':fd_observe_calls,'first_tick':'forward difference','maximum_angular_speed_rad_s':maximum_speed})
  return {'id':cid,'method':outcome.get('method','mem0'),'variant':outcome['variant'],'horizon':outcome['execution_horizon'],'layout':outcome['layout'],'role':outcome['score_role'],'stage':'diagnostic','strict_v1':strict_result,'strict_fdvel_v1':fd_result,'placement_v1_1':placement_result,'physics_ticks':count,'trace_sha256':h.hexdigest(),'actual_time_first':first,'actual_time_last':last,'archive_sha256':receipt['sha256'],'archive_bytes':receipt['bytes'],'all_oracles_replayed_independently':True,'strict_velocity_predicate_present':False}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,default=4);a=parser.parse_args()
 archive=json.loads((F/'portable_job_v3/RUNTIME_ARCHIVE_STATUS.json').read_text())
 result=json.loads((F/'NEW_ARCHIVE_THREE_METRICS_v2.json').read_text())if(F/'NEW_ARCHIVE_THREE_METRICS_v2.json').exists()else{'rows':{},'errors':{}}
 result.update(CPU_only=True,new_simulations=0,common_script_sha256=hashlib.sha256(COMMON.read_bytes()).hexdigest(),oracle_source_sha256=EXPECTED,first_tick='forward_difference',started_epoch=time.time(),complete=False)
 todo=[(cid,r['receipt'])for cid,r in archive['cases'].items()if r['status']=='verified'and cid not in result['rows']and cid not in result['errors']][:a.limit]
 with m.dt.Connections(want_bj_sftp=True)as c:
  m.st.load_approved_token(c.bj_sftp);assert m.pt.api('GET','/pt/api/ai/capabilities',connection=c)['status']==200
  for cid,receipt in todo:
   assert receipt['source_id']=='ic0fsbfuxw9e7drmt7p09nkf6'and receipt['key'].startswith(PREFIX)and receipt['verified']and receipt['bytes']<=128<<20
   response=m.pt.api('POST','/pt/api/ai/files/download-presign',{'source_id':receipt['source_id'],'key':receipt['key'],'expires_seconds':900},connection=c)
   assert response['status']==200;body=response['data'];body=body.get('data',body);url=body['url'];u=urllib.parse.urlsplit(url)
   assert u.scheme=='https'and u.hostname=='zenith-a02012413.bj.bcebos.com'and u.path=='/'+receipt['key']and not u.username and not u.password and not u.fragment and u.port in[None,443]
   try:
    with OP.open(urllib.request.Request(url,method='GET'),timeout=120)as stream:assert stream.status==200;data=stream.read(receipt['bytes']+1)
    row=evaluate(data,cid,receipt);result['rows'][cid]=row
    print(json.dumps({'id':cid,'ticks':row['physics_ticks'],'FD_unknown':row['strict_fdvel_v1']['unknown'],'phase':row['placement_v1_1']['physical_phase']}),flush=True)
   except Exception as e:
    result['errors'][cid]={'error_type':type(e).__name__,'scientific_results_changed':False};save(result);raise
   save(result)
 result.update(complete=True,finished_epoch=time.time(),cases_scored=len(result['rows']));save(result)
if __name__=='__main__':main()
