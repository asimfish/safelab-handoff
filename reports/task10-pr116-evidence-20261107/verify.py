"""Verify all114 inference rows' report aliases without changing data or executing sources."""
from pathlib import Path
import json,hashlib,re,argparse
D=Path(__file__).parent;R=D.parent.parent

def verify(source=None):
 m=json.loads((D/'mapping.json').read_text());assert m['scope_rows']==114 and len(m['direct_missing_files'])==10 and len(m['objects'])==38
 by={o['path']:o for o in m['objects']}
 for o in m['objects']:
  assert o['anonymous_GET_verified'] and o['source_commit']==m['source_commit']
  assert o['url'].startswith('https://zenith-a02012413.tos-cn-beijing.volces.com/liyufeng/safelab-public/reports-v1/10/pr95-ec1fb488/') and '?' not in o['url']
  if o['path'].endswith('.json'):
   p=json.loads((R/o['path']).read_text());assert p['kind']=='external_evidence_pointer' and p['source_url']==o['url'] and p['source_sha256']==o['sha256'] and p['source_bytes']==o['bytes']
  if source:
   b=(source/o['path']).read_bytes();assert len(b)==o['bytes'] and hashlib.sha256(b).hexdigest()==o['sha256']
 data=json.loads((R/'data.json').read_text());rows=[e for e in data['evaluations'] if e.get('id','').startswith('task10-inference-20261106-')]
 refs=set()
 for e in rows:refs.update(x.rstrip('.') for x in re.findall(r'reports/[A-Za-z0-9_./-]+',json.dumps(e)))
 absent=[p for p in refs if not(R/p).is_file()];assert not absent,absent
 print(json.dumps({'source_scope_rows':114,'current_inference_rows':len(rows),'objects':38,'direct_missing_repaired':10,'unresolved_current_report_references':0,'source_bytes_checked':source is not None,'data_sha256':hashlib.sha256((R/'data.json').read_bytes()).hexdigest()}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--source-root',type=Path);verify(a.parse_args().source_root)
