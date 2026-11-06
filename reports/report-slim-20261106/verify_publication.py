"""Offline pointer/manifest and optional preserved-original verification."""
from pathlib import Path
import argparse,json,hashlib,gzip,importlib.util
HERE=Path(__file__).parent;ROOT=HERE.parent.parent
spec=importlib.util.spec_from_file_location('restore',HERE/'restore.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
def verify(archive=None):
 m=json.loads((HERE/'manifest.json').read_text());assert len(m['objects'])==112
 assert hashlib.sha256((ROOT/'data.json').read_bytes()).hexdigest()==m['data_json_sha256']
 for o in m['objects']:
  path=r.validate(o);p=ROOT/path
  if p.suffix=='.csv':p=p.with_suffix('.csv.migration.json')
  pointer=json.loads(p.read_text());assert pointer['kind']=='compressed_evidence_pointer' and pointer['original_path']==o['path']
  assert pointer['anonymous_GET_verified'] is True
  assert pointer['asset']=={k:v for k,v in o.items() if k not in ['path','anonymous_GET_verified']}
  if archive:
   b=(archive/path).read_bytes();wire=gzip.compress(b,mtime=0);assert r.decode(o,wire)==b
 print(json.dumps({'objects':len(m['objects']),'data_json_sha256':m['data_json_sha256'],'original_verification':archive is not None}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--original-root',type=Path);verify(a.parse_args().original_root)
