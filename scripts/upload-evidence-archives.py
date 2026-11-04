"""Run on an authorized node with tos2.9.3 and ZENITH_API_TOKEN in environment.
No bucket-policy/CORS mutation, no overwrite, no deletion, no credential output.
"""
import argparse,hashlib,json,logging,os,pathlib,urllib.request,urllib.error,urllib.parse,subprocess,shlex
logging.getLogger('tos').setLevel(logging.CRITICAL)
ap=argparse.ArgumentParser();ap.add_argument('repo',type=pathlib.Path);ap.add_argument('plan',type=pathlib.Path);ap.add_argument('receipt',type=pathlib.Path);a=ap.parse_args();root=a.repo.resolve();items=json.loads(a.plan.read_text())['objects'];token=os.environ['ZENITH_API_TOKEN'];base=os.environ.get('ZENITH_API_BASE','https://zenith.bza.edu.cn/pt/api2')
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
def request(path,body=None):
 if os.environ.get('ZENITH_API_SSH_TARGET'):
  assert base=='https://zenith.bza.edu.cn/pt/api2'
  remote="""import sys,json,urllib.request,urllib.error,os
x=json.load(sys.stdin);os.environ['ZENITH_API_TOKEN']=x.pop('token')
req=urllib.request.Request(x['url'],data=None if x['body'] is None else json.dumps(x['body']).encode(),headers={'Authorization':'Bearer '+os.environ['ZENITH_API_TOKEN'],'Content-Type':'application/json'})
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with op.open(req,timeout=30) as r:sys.stdout.write(json.dumps({'status':r.status,'data':json.load(r)}))
except urllib.error.HTTPError as e:sys.stdout.write(json.dumps({'status':e.code}))
except Exception as e:sys.stdout.write(json.dumps({'status':0,'error_type':type(e).__name__}))
"""
  r=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=8','-p',os.environ.get('ZENITH_API_SSH_PORT','4009'),os.environ['ZENITH_API_SSH_TARGET'],'python3 -c '+shlex.quote(remote)],input=json.dumps({'token':token,'url':base+path,'body':body}),text=True,capture_output=True,timeout=45)
  if r.returncode:raise RuntimeError('SSH transport failed; credential output suppressed')
  result=json.loads(r.stdout)
  if result['status']!=200:raise RuntimeError('API status '+str(result['status'])+' endpoint '+base+path)
  return result['data']
 req=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='GET' if body is None else 'POST')
 with op.open(req,timeout=30) as r:return json.load(r)
def anonymous(item):
 try:
  with op.open(urllib.request.Request(item['url'],headers={'Cache-Control':'no-cache'}),timeout=45) as r:
   digest=hashlib.sha256();n=0
   while True:
    b=r.read(1048576)
    if not b:break
    n+=len(b);digest.update(b)
   assert n==item['bytes'] and digest.hexdigest()==item['sha256'],'anonymous_GET_integrity_mismatch'
   return True
 except urllib.error.HTTPError as e:
  if e.code in (403,404):return False
  raise
request('/ai/capabilities');sts=request('/ai/files/bucket-sts',{'source_id':'k32181r1qe5gh73u8yvqyur5e','duration_seconds':900});assert sts['bucket']=='zenith-a02012413' and sts['vendor']=='volcengine';assert urllib.parse.urlsplit(sts['endpoint']).hostname.endswith('.volces.com')
import tos
client=tos.TosClientV2(sts['access_key_id'],sts['secret_access_key'],endpoint=sts['endpoint'],region=sts['region'],security_token=sts['session_token'],max_retry_count=1)
results=[]
try:
 for item in items:
  path=(root/item['path']).resolve();assert path.is_relative_to(root/'reports') and not (root/item['path']).is_symlink();assert item['key'].startswith('liyufeng/safelab-public/reports-v1/'+item['task']+'/') and '..' not in item['key'].split('/');assert item['url']=='https://zenith-a02012413.tos-cn-beijing.volces.com/'+item['key'];raw=path.read_bytes();assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
  if not anonymous(item):
   exists=False
   try:
    head=client.head_object(sts['bucket'],item['key']);exists=True
   except tos.exceptions.TosServerError as e:
    if e.status_code!=404:raise
   if exists:
    response=client.get_object(sts['bucket'],item['key']);old=response.read();assert len(old)==len(raw) and hashlib.sha256(old).hexdigest()==item['sha256'],'existing_object_mismatch_refuse_overwrite';client.put_object_acl(sts['bucket'],item['key'],acl=tos.enum.ACLType.ACL_Public_Read)
   else:
    client.put_object(sts['bucket'],item['key'],content=raw,content_length=len(raw),content_sha256=item['sha256'],acl=tos.enum.ACLType.ACL_Public_Read,forbid_overwrite=True)
   assert anonymous(item),'not_anonymous_public_after_upload'
  results.append({**item,'public_get_verified':True,'verified_bytes':len(raw),'verified_sha256':item['sha256']});a.receipt.write_text(json.dumps({'objects':results},indent=2));print('verified',item['path'],flush=True)
finally:client.close()
