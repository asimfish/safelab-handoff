"""Restore immutable fefad99 reports into a NEW directory; never overwrite."""
import argparse,json,gzip,hashlib,urllib.request
from pathlib import Path,PurePosixPath
D=Path(__file__).parent
def decode(o,b):
 assert len(b)==o['bytes'] and hashlib.sha256(b).hexdigest()==o['sha256']
 raw=gzip.decompress(b)
 assert len(raw)==o['decoded_bytes'] and hashlib.sha256(raw).hexdigest()==o['decoded_sha256']
 return raw
def main(root):
 root.mkdir(parents=True,exist_ok=False)
 m=json.loads(gzip.decompress((D/'manifest.json.gz').read_bytes()))
 for o in m['objects']:
  p=PurePosixPath(o['path']);assert not p.is_absolute() and p.parts[0]=='reports' and '..' not in p.parts
  assert o['url'].startswith('https://zenith-a02012413.tos-cn-beijing.volces.com/liyufeng/safelab-public/reports-v1/visualization-slim-0920-20261107/')
  with urllib.request.urlopen(o['url'],timeout=60) as r:b=r.read(o['bytes']+1)
  dest=root.joinpath(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb') as f:f.write(decode(o,b))
 print('restored',len(m['objects']))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('new_directory',type=Path);main(a.parse_args().new_directory)
