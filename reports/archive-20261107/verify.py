import argparse,json,gzip,hashlib
from pathlib import Path
D=Path(__file__).parent
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('original_root',type=Path);a=p.parse_args();m=json.loads(gzip.decompress((D/'manifest.json.gz').read_bytes()))
 for o in m['objects']:
  b=(a.original_root/o['path']).read_bytes();assert len(b)==o['decoded_bytes'] and hashlib.sha256(b).hexdigest()==o['decoded_sha256']
 print('verified',len(m['objects']),'original reports; data SHA',m['data_json_sha256'])
