#!/usr/bin/env python3
"""Losslessly copy derived logs to gzip; retain byte-bound old paths for a release."""
import argparse,gzip,hashlib,json,pathlib,subprocess,datetime,re
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--wire-budget',type=int,default=180000);p.add_argument('--release',required=True);a=p.parse_args();archive=pathlib.Path(a.archive).resolve()
 if not re.fullmatch(r'[A-Za-z0-9_-]+',a.release):raise SystemExit('Invalid release identity')
 allowed=pathlib.Path('/projects/a02012413/buckets/zenith-a02012413/liyufeng').resolve()
 if not archive.is_relative_to(allowed) or archive.is_relative_to(ROOT):raise SystemExit('Archive must be outside Git in the allowed owned bucket path')
 ledger_path=ROOT/'media/migrations'/('frame-log-'+a.release+'.json')
 if ledger_path.exists():raise SystemExit('Migration intent already recorded; no files changed')
 index_path=ROOT/'media/index.json';index=json.loads(index_path.read_text());manifests={}
 for ref in index['manifests']:
  name=ref['url'].removeprefix('https://asimfish.github.io/safelab-handoff/');path=ROOT/name
  if not name.startswith('media/manifests/'):raise SystemExit('Unexpected manifest URL')
  manifests[name]=json.loads(path.read_text())
 candidates={}
 for name,j in manifests.items():
  for c in j['cases']:
   old=c.get('frame_log')
   if not old or old.get('encoding','identity')!='identity':continue
   rel=old['url'].removeprefix('https://asimfish.github.io/safelab-handoff/')
   if (ROOT/rel).resolve()!=(ROOT/rel).absolute() or not (ROOT/rel).resolve().is_relative_to(ROOT.resolve()):raise SystemExit('Source log escapes repository')
   if not rel.startswith('media/frame_logs/') or '..' in pathlib.PurePosixPath(rel).parts or not rel.endswith('.json'):raise SystemExit('Bad source log path')
   b=(ROOT/rel).read_bytes()
   if len(b)>2000000:raise SystemExit('Source log exceeds2MB decoded bound')
   if sha(b)!=old['sha256'].removeprefix('sha256:') or len(b)!=old['bytes']:raise SystemExit('Old identity mismatch')
   obj=json.loads(b)
   if obj['case_id']!=c['case_id']:raise SystemExit('Old case mismatch')
   dest=archive/rel
   if not dest.resolve().is_relative_to(archive) or dest.resolve()!=dest.absolute():raise SystemExit('Archive path contains a symlink or escapes archive')
   dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists() and dest.read_bytes()!=b:raise SystemExit('Archive collision')
   if not dest.exists():dest.write_bytes(b)
   if sha(dest.read_bytes())!=sha(b):raise SystemExit('Archive SHA mismatch')
   wire=gzip.compress(b,compresslevel=9,mtime=0)
   if gzip.decompress(wire)!=b:raise SystemExit('Not byte equivalent')
   candidates.setdefault(rel,{'raw':b,'wire':wire,'refs':[]})['refs'].append((name,c,old))
 selected=[];used=0
 for rel,v in sorted(candidates.items(),key=lambda item:(len(item[1]['wire'])/len(item[1]['raw']),item[0])):
  if used+len(v['wire'])>a.wire_budget:continue
  used+=len(v['wire']);selected.append((rel,v))
 records=[];changed=set();now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 for rel,v in selected:
  newrel=rel+'.gz';dest=ROOT/newrel
  if dest.exists() and dest.read_bytes()!=v['wire']:raise SystemExit('gzip collision')
  dest.write_bytes(v['wire'])
  for name,c,old in v['refs']:
   new={**old,'url':old['url']+'.gz','sha256':sha(v['wire']),'bytes':len(v['wire']),'encoding':'gzip','decoded_sha256':sha(v['raw']),'decoded_bytes':len(v['raw'])}
   if 'path'in new:new['path']=newrel
   c['frame_log_previous']=old;c['frame_log']=new;changed.add(name)
  records.append({'path':rel,'gzip_path':newrel,'original_sha256':sha(v['raw']),'original_bytes':len(v['raw']),'gzip_sha256':sha(v['wire']),'gzip_bytes':len(v['wire']),'case_ids':[c['case_id'] for _,c,_ in v['refs']]})
 for name in changed:
  manifests[name]['updated_at']=now;(ROOT/name).write_text(json.dumps(manifests[name],ensure_ascii=False,separators=(',',':'))+'\n')
 for ref in index['manifests']:
  name=ref['url'].removeprefix('https://asimfish.github.io/safelab-handoff/')
  if name in changed:ref['sha256']=sha((ROOT/name).read_bytes());ref['updated_at']=now
 index['updated_at']=now;index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
 ledger={'schema_version':'safelab-gzip-migration-v1','release':a.release,'created_at':now,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'retention':'Old public paths retained through this published release. Retire only in a later deployed release after old/new anonymous GET and decoded SHA verification. Source copies stay archived.','logs':records,'source_bytes':sum(x['original_bytes'] for x in records),'gzip_bytes':used,'preserved_archived_plain_logs':len(candidates)}
 out=ROOT/'media/migrations'/('frame-log-'+a.release+'.json');out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():raise SystemExit('Ledger already exists; do not repeat a migration intent')
 out.write_text(json.dumps(ledger,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps({k:v for k,v in ledger.items() if k!='logs'}))
if __name__=='__main__':main()
