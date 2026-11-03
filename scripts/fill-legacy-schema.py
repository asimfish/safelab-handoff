"""Fill missing historical metadata only; never alter measured values or v1/v1.1 rows."""
from pathlib import Path
import copy,json
P=Path(__file__).resolve().parents[1]/'data.json'
data=json.loads(P.read_text());before=copy.deepcopy(data);changed=[]
for e in data['evaluations']:
    if e.get('protocol_version') in ('SafeLab-Eval-v1','SafeLab-Eval-v1.1'):continue
    defaults={'protocol_version':'legacy','stage':'diagnostic'if'diagnostic'in str(e.get('protocol_version','')).lower()else'legacy',
              'topology':{'num_envs_actual':None,'procs_per_gpu':None,'gpu_type':None},
              'preprocess_resize':None,'condition_version':None,'scene_list_hash':None,
              'lr_split':None,'mean_phase':None,'phase_hist':None,'wilson95':None}
    fields=[]
    for k,v in defaults.items():
        if k not in e:e[k]=v;fields.append(k)
    if e['stage']=='legacy'and'legacy_protocol'not in e:e['legacy_protocol']=e.get('protocol');fields.append('legacy_protocol')
    if fields:changed.append({'id':e['id'],'added':fields})
for old,new in zip(before['evaluations'],data['evaluations']):
    assert all(new[k]==v for k,v in old.items()),'existing evidence changed'
for k,v in before.items():
    if k!='evaluations':assert data[k]==v,'unrelated section changed'
assert len(before['evaluations'])==len(data['evaluations'])
P.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'filled_rows':len(changed),'preexisting_values_unchanged':True,'formal_rows_not_modified':True}))
