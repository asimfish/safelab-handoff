"""Paired method comparison from a complete, published fixed50 case manifest."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
p=argparse.ArgumentParser();p.add_argument('cases',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
raw=args.cases.read_bytes();data=json.loads(raw);methods=['mem0_original','ours_aligned'];maps={m:{}for m in methods}
for c in data['cases']:
 if c['method']in maps:
  key=(c['scene_index'],c['seed']);assert key not in maps[c['method']];maps[c['method']][key]=c
assert set(maps[methods[0]])==set(maps[methods[1]]) and len(maps[methods[0]])==50
keys=sorted(maps[methods[0]]);assert {i for i,s in keys}==set(range(25))|set(range(50,75))
for m in methods:assert all(c.get('slew_verified')for c in maps[m].values()) and all(not c.get('unknown')for c in maps[m].values())
idx=np.random.default_rng(20261106).integers(50,size=(10000,50))
out={'stage':'diagnostic','formal_score_eligible':False,'setting':data['setting'],'contrast':'TTC aligned minus Mem0','paired_n':50,'unknown':0,'bootstrap_seed':20261106,'bootstrap_replicates':10000,'source_case_manifest':args.cases.name,'source_case_manifest_sha256':hashlib.sha256(raw).hexdigest(),'protocols':{}}
for protocol in ['placement-v1.1','SafeLab-Eval-v1.2-relaxed','SafeLab-Eval-v1.3-lenient']:
 a=np.array([maps[methods[0]][i]['protocols'][protocol]['phase']for i in keys]);b=np.array([maps[methods[1]][i]['protocols'][protocol]['phase']for i in keys]);delta=b-a
 sa=np.array([maps[methods[0]][i]['protocols'][protocol]['success']for i in keys],dtype=int);sb=np.array([maps[methods[1]][i]['protocols'][protocol]['success']for i in keys],dtype=int);ds=sb-sa
 out['protocols'][protocol]={'Mem0_success':int(sa.sum()),'TTC_success':int(sb.sum()),'Mem0_mean_phase':float(a.mean()),'TTC_mean_phase':float(b.mean()),'paired_mean_difference':float(delta.mean()),'paired_mean_difference_ci95':np.quantile(delta[idx].mean(axis=1),[.025,.975]).tolist(),'success_rate_difference':float(ds.mean()),'success_rate_difference_ci95':np.quantile(ds[idx].mean(axis=1),[.025,.975]).tolist()}
args.output.write_text(json.dumps(out,indent=2));print(json.dumps(out))
