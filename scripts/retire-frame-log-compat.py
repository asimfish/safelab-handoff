#!/usr/bin/env python3
"""Retire only old published derived copies after a verified release window."""
import argparse,datetime,hashlib,json,pathlib,re,subprocess,io,gzip
ROOT=pathlib.Path(__file__).resolve().parents[1]
ARCHIVE_ROOT=pathlib.Path('/projects/a02012413/buckets/zenith-a02012413/liyufeng').resolve()
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--release',required=True);p.add_argument('--receipt',required=True);p.add_argument('--archive',required=True);p.add_argument('--publication-commit',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
 if not re.fullmatch(r'[a-zA-Z0-9_-]+',a.release) or not re.fullmatch(r'[a-f0-9]{40}',a.publication_commit):raise SystemExit('Invalid release identity')
 target=ROOT/'media/migrations'/('retired-'+a.release+'.json')
 if target.exists():raise SystemExit('Retirement already recorded; no files changed')
 ledger=json.loads((ROOT/'media/migrations'/('frame-log-'+a.release+'.json')).read_text());rb=pathlib.Path(a.receipt).read_bytes();receipt=json.loads(rb)
 if receipt.get('online')is not True or receipt.get('release')!=a.release or receipt.get('verified')!=len(ledger['logs']):raise SystemExit('Complete online receipt required')
 verified={r['path']:r for r in receipt['verification']}
 now=datetime.datetime.now(datetime.timezone.utc);stamp=datetime.datetime.fromisoformat(receipt['verified_at'].replace('Z','+00:00'));age=(now-stamp).total_seconds()
 if age<0:raise SystemExit('Receipt timestamp is in the future')
 archive=pathlib.Path(a.archive).resolve();allowed=ARCHIVE_ROOT
 if not archive.is_relative_to(allowed)or archive.is_relative_to(ROOT):raise SystemExit('Archive must be preserved outside Git in the allowed owned root')
 candidates={}
 for item in ledger['logs']:
  name=item['path'];rel=pathlib.PurePosixPath(name)
  if not name.startswith('media/frame_logs/')or '..'in rel.parts or not name.endswith('.json'):raise SystemExit('Not a plain derived-log path')
  old=ROOT/name;gz=ROOT/item['gzip_path'];proof=verified.get(item['gzip_path'],{})
  if old.is_symlink()or gz.is_symlink()or not old.is_file()or not gz.is_file():raise SystemExit('Missing/nonregular compatibility copy')
  if old.resolve()!=old.absolute()or gz.resolve()!=gz.absolute()or not old.resolve().is_relative_to(ROOT.resolve())or not gz.resolve().is_relative_to(ROOT.resolve()):raise SystemExit('Compatibility path escapes repository')
  b=old.read_bytes();wire=gz.read_bytes()
  if len(b)>2000000 or len(wire)>2000000:raise SystemExit('Compatibility log exceeds2MB bound')
  with gzip.GzipFile(fileobj=io.BytesIO(wire))as f:decoded=f.read(2000001)
  if len(decoded)>2000000:raise SystemExit('Decoded log exceeds2MB bound')
  if sha(b)!=item['original_sha256']or sha(wire)!=item['gzip_sha256']or decoded!=b:raise SystemExit('Published candidate changed')
  if (archive/name).resolve()!=(archive/name).absolute()or not (archive/name).resolve().is_relative_to(archive)or (archive/name).read_bytes()!=b:raise SystemExit('Preserved original archive mismatch')
  if proof.get('decoded_sha256')!=item['original_sha256']or proof.get('old_url_retained')is not True or proof.get('content_encoding')is not None:raise SystemExit('Online original/gzip verification missing')
  candidates[name]=item
 index_path=ROOT/'media/index.json';index=json.loads(index_path.read_text());updated={};bound=set()
 for ref in index['manifests']:
  name=ref['url'].removeprefix('https://asimfish.github.io/safelab-handoff/')
  if not name.startswith('media/manifests/')or '..'in pathlib.PurePosixPath(name).parts:raise SystemExit('Bad manifest path')
  path=ROOT/name;obj=json.loads(path.read_text());changed=False
  for c in obj['cases']:
   prev=c.get('frame_log_previous');old=prev.get('url','').removeprefix('https://asimfish.github.io/safelab-handoff/')if prev else None
   if old not in candidates:continue
   item=candidates[old];current=c['frame_log']
   if prev['sha256'].removeprefix('sha256:')!=item['original_sha256']or current['sha256']!=item['gzip_sha256']or c['case_id']not in item['case_ids']:raise SystemExit('Manifest predecessor binding changed')
   del c['frame_log_previous'];bound.add(old);changed=True
  if changed:obj['updated_at']=now.isoformat();updated[name]=(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n').encode()
 if bound!=set(candidates):raise SystemExit('Every retired log must have a bound canonical successor')
 result={'schema_version':'safelab-gzip-retirement-v1','release':a.release,'publication_commit':a.publication_commit,'receipt_sha256':sha(rb),'receipt_verified_at':receipt['verified_at'],'retention_elapsed_s':round(age,3),'retention_minimum_s':600,'retired_public_paths':sorted(candidates),'retired_bytes':sum(x['original_bytes']for x in candidates.values()),'source_archive_preserved':True}
 if not a.apply:print(json.dumps({**result,'preview_only':True,'ready':age>=600}));return
 if age<600:raise SystemExit('Published compatibility window has not elapsed; no files changed')
 for name,b in updated.items():(ROOT/name).write_bytes(b)
 for ref in index['manifests']:
  name=ref['url'].removeprefix('https://asimfish.github.io/safelab-handoff/')
  if name in updated:ref['sha256']=sha(updated[name]);ref['updated_at']=now.isoformat()
 index['updated_at']=now.isoformat();index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
 for name in candidates:(ROOT/name).unlink() # Only expired GitHub derived copies; never touches preserved archives.
 target.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps({k:v for k,v in result.items()if k!='retired_public_paths'}))
if __name__=='__main__':main()
