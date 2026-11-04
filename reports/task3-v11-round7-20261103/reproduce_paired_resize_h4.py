"""CPU-only reproduction of the seed0 diagnostic paired bootstrap."""
from pathlib import Path
import json,numpy as np
rows=json.loads(Path(__file__).with_name('paired-resize-h4-cases.json').read_text())['rows'];assert len(rows)==100;out={}
for field in ['strict_success','placement_success']:
 a=np.asarray([[int(x['ttc'][field]),int(x['mem0'][field])]for x in rows]);d=a[:,0]-a[:,1];rng=np.random.default_rng(10350702);boot=np.zeros(20000)
 for side in ['left','right']:
  ix=np.asarray([i for i,x in enumerate(rows)if x['side']==side]);assert len(ix)==50;boot+=d[rng.choice(ix,(20000,len(ix)),replace=True)].sum(axis=1)/100
 out[field]={'ttc':int(a[:,0].sum()),'mem0':int(a[:,1].sum()),'difference_pp':float(100*d.mean()),'bootstrap_95_pp':list(100*np.quantile(boot,[.025,.975]))}
print(json.dumps(out,indent=2))
