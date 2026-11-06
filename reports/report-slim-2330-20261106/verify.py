from pathlib import Path
import json,hashlib,gzip,importlib.util,argparse
D=Path(__file__).parent;ROOT=D.parent.parent
spec=importlib.util.spec_from_file_location('restore',D/'restore.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
def main(archive):
 m=json.loads(gzip.decompress((D/'manifest.json.gz').read_bytes()));assert len(m['objects'])==220
 assert hashlib.sha256((ROOT/'data.json').read_bytes()).hexdigest()==m['data_json_sha256']
 html=0
 for i,o in enumerate(m['objects']):
  p=ROOT/r.validate(o)
  if p.suffix=='.html':
   html+=1;wire=p.with_name(p.name+'.gz').read_bytes();source=r.decode(o,wire)
   assert o['sha256'] in p.read_text() and o['decoded_sha256'] in p.read_text()
  else:
   if p.suffix!='.json':p=p.with_name(p.name+'.migration.json')
   pointer=json.loads(p.read_text());assert pointer['kind']=='compressed_evidence_pointer' and pointer['object_index']==i and pointer['original_path']==o['path']
   assert (p.parent/pointer['migration_manifest']).resolve()==(D/'manifest.json.gz').resolve()
   source=(archive/o['path']).read_bytes() if archive else None
  if archive:
   b=(archive/o['path']).read_bytes();assert r.decode(o,gzip.compress(b,mtime=0))==b
 print(json.dumps({'objects':220,'inline_html':html,'data_json_sha256':m['data_json_sha256'],'originals_checked':archive is not None}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--original-root',type=Path);main(a.parse_args().original_root)
