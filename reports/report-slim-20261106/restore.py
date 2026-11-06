"""Restore exact report source bytes into a NEW directory; never overwrite a tree."""
import argparse,gzip,hashlib,json
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit
from urllib.request import urlopen

def validate(o):
 p=PurePosixPath(o['path']);u=urlsplit(o['url'])
 if not str(p).startswith('reports/') or '..' in p.parts or p.is_absolute() or str(p)!=o['path']:raise ValueError('invalid report path')
 if u.scheme!='https' or u.netloc!='zenith-a02012413.tos-cn-beijing.volces.com' or not u.path.startswith('/liyufeng/safelab-public/reports-v1/visualization-slim-20261106/') or u.query or u.fragment or '%' in u.path:raise ValueError('unapproved evidence URL')
 for k in ['sha256','decoded_sha256']:
  v=o[k]
  if len(v)!=64 or any(c not in '0123456789abcdef' for c in v):raise ValueError('invalid digest')
 if not 0<o['bytes']<=200000 or not 0<o['decoded_bytes']<=200000:raise ValueError('oversized evidence')
 return p

def decode(o,b):
 validate(o)
 if len(b)!=o['bytes'] or hashlib.sha256(b).hexdigest()!=o['sha256']:raise ValueError('wire SHA/bytes mismatch')
 import io
 with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:decoded=f.read(o['decoded_bytes']+1)
 if len(decoded)!=o['decoded_bytes'] or hashlib.sha256(decoded).hexdigest()!=o['decoded_sha256']:raise ValueError('decoded SHA/bytes mismatch')
 return decoded

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=Path);a=parser.parse_args();m=json.loads(Path(__file__).with_name('manifest.json').read_text())
 for o in m['objects']:validate(o)
 a.destination.mkdir(exist_ok=False,parents=False)
 for o in m['objects']:
  with urlopen(o['url'],timeout=30) as r:b=r.read(o['bytes']+1)
  content=decode(o,b);p=a.destination/validate(o);p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(content)
  print(o['path'])
if __name__=='__main__':main()
