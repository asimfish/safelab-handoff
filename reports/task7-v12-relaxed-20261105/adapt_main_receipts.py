"""Main200 only: map frozen original CPU receipts into aggregation fields.

The source source protocols and bytes are retained, never rewritten. Prefix
mapping follows the root-approved source ordinal-phase rule, not new geometry.
"""
from pathlib import Path
import argparse,hashlib,json,time

HERE=Path(__file__).resolve().parent
IDENTITY_SHA='21cf4da87fa3c73974fe8466faad6c7fcd49687a1ac056e2376c51fb93a82ae6'
ALIASES={'strict':'strict','v1.1':'v1.1','relaxed':'v1.2-relaxed'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'file':str(p),'bytes':Path(p).stat().st_size,'sha256':sha(p)}
def adapt(identities,source_records):
    expected=identities['expected_cases'];byid={x['case_id']:x for x in expected}
    assert len(byid)==len(expected)==200
    configs=[]
    for variant,family in [('mem0_30k','Mem0'),('ours_aligned_30k','TTC')]:
        cases=[x for x in expected if x['variant']==variant];assert len(cases)==100
        assert len({(x['condition'],x['source_condition_version'],x['horizon'],x['original_scene_list_sha256'],x['executed_scene_contract_sha256'])for x in cases})==1
        # Preserve both source condition fields; do not collapse different chains.
        condition=cases[0]['condition']+'::'+cases[0]['source_condition_version']
        configs.append({'configuration_id':variant,'family':family,'expected_n':100,'condition_version':condition,
          'source_condition':cases[0]['condition'],'source_condition_version':cases[0]['source_condition_version'],
          'horizon':8,'camera':'chest','scene_list_hash':'sha256:'+cases[0]['original_scene_list_sha256'],
          'executed_scene_contract_sha256':cases[0]['executed_scene_contract_sha256'],
          'cases':[{'case_id':x['case_id'],'scene_id':x['scene_id'],'seed':x['seed'],'order':x['order'],'condition_version':condition}for x in cases]})
    cfg={c['configuration_id']:c for c in configs};out=[];seen=set()
    for row in source_records:
        key=row['case_id'];assert key in byid and key not in seen;seen.add(key);identity=byid[key]
        p=Path(row['receipt']['file']);assert p.is_file()and p.stat().st_size<1<<20
        assert sha(p)==row['receipt']['sha256'];source=json.loads(p.read_bytes())
        assert source['case_id']==key and source['variant']==row['variant']==identity['variant']
        assert source['order']==identity['order']and source['seed']==identity['seed']and source['horizon']==8
        assert source['condition']==identity['condition']and source['original_stop_extended']is False
        assert source['protocols']==row['protocols'],'Index protocols must equal original receipt bytes'
        available=source['raw_SHA_verified']is True
        if available:
            assert source['status']=='raw_full_SHA_CPU_verified'
            assert source['original_v11_all_rows_exact']is True and source['original_strict_all_events_exact']is True
            raw=[{k:source['raw'][k]for k in ['file','bytes','sha256']}]
        else:
            assert source['status']=='unknown'and source.get('raw')is None
            assert all(o['verdict']=='U'and o['success']is None and o['phase']is None for o in source['protocols'].values())
            raw=[]
        oracles={}
        for canonical,original in ALIASES.items():
            o=source['protocols'][original];success=o['success'];phase=o['phase']
            assert o['verdict']==('U'if success is None else'S'if success else'F')
            per_k={str(k):('S'if phase is not None and phase>=k else'F'if o['verdict']=='F'else'U')for k in range(1,8)}
            oracles[canonical]={'success':success,'phase':phase if success is not None else None,
              'observed_phase_lower_bound':phase,'per_k':per_k,'source_protocol_key':original,
              'source_oracle_record':o,'source_receipt':ref(p)}
        out.append({'configuration_id':row['variant'],'case_id':key,'scene_id':identity['scene_id'],'seed':identity['seed'],
          'order':identity['order'],'condition_version':cfg[row['variant']]['condition_version'],'final':True,
          'closure_valid':available,'raw_available':available,'raw_refs':raw,'oracles':oracles,
          'source_receipt':ref(p),'source_original_S_file':row['receipt'].get('original_S_file'),
          'source_raw_SHA_verification_reused':True,'new_raw_reads':0})
    return {'schema':'task7_relaxed_rescore_aggregation_manifest.v1','bootstrap_replicates':10000,'bootstrap_seed':20261105,
      'configurations':configs,'pairs':[{'left':'mem0_30k','right':'ours_aligned_30k'}]},out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--identities',type=Path,required=True);p.add_argument('--index',type=Path,required=True);p.add_argument('--index-sha256',required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    assert sha(a.identities)==IDENTITY_SHA and sha(a.index)==a.index_sha256
    source=json.loads(a.index.read_bytes());m,r=adapt(json.loads(a.identities.read_bytes()),source['records'])
    assert not a.output_dir.exists();a.output_dir.mkdir()
    m['source_refs']={'identities':ref(a.identities),'CPU_record_index':ref(a.index),'adapter_source_sha256':sha(__file__)}
    for name,v in [('MANIFEST.json',m),('RECORDS.json',{'schema':'task7_relaxed_selected_source_records.v1','records':r,'source_refs':m['source_refs']})]:
        (a.output_dir/name).write_text(json.dumps(v,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
    report={'epoch':time.time(),'expected':200,'adapted':len(r),'raw_available':sum(x['raw_available']for x in r),
      'raw_unknown':sum(not x['raw_available']for x in r),'complete':len(r)==200,'source_receipt_bytes_SHA_verified':len(r),
      'source_fields_rewritten':False,'new_oracle_raw_NN_GPU_calls':0,'sources':m['source_refs']}
    (a.output_dir/'ADAPTER_RECEIPT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'directory':str(a.output_dir),'receipt':ref(a.output_dir/'ADAPTER_RECEIPT.json'),'records':ref(a.output_dir/'RECORDS.json')}))
