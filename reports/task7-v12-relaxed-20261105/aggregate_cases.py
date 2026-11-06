"""CPU aggregation only: consumes authoritative per-case oracle verdicts.

No geometry, oracle implementation, label derivation, raw scan or model call.
"""
from collections import Counter,defaultdict
from pathlib import Path
import argparse,hashlib,json,math,random,time

ORACLES=('strict','v1.1','relaxed');KS=tuple(range(1,8))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def wilson(s,n):
    if not n:return None
    z=1.959963984540054;p=s/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return {'low':max(0,c-h),'high':min(1,c+h),'confidence':.95}
def percentile(values,q):
    v=sorted(x for x in values if x is not None)
    if not v:return None
    i=(len(v)-1)*q;lo=math.floor(i);hi=math.ceil(i);return v[lo]+(v[hi]-v[lo])*(i-lo)
def interval(values):return {'CI95':[percentile(values,.025),percentile(values,.975)],'valid_replicates':sum(x is not None for x in values)}
def identity(case):return(case['scene_id'],case['seed'],case['order'],case['condition_version'])
def counts(statuses,n,complete):
    c=Counter(statuses);assert set(c)<={'S','F','U'}
    valid=c['S']+c['F']
    return {'S':c['S'],'F':c['F'],'U':c['U'],'total_n':n,'valid_verdict_n':valid,
      'pending_n':n-len(statuses),'SR_total_denominator':c['S']/n if complete and n else None,
      'complete_verdict_SR':c['S']/n if complete and n and not c['U']else None,
      'SR_identification_bounds':[c['S']/n,(c['S']+c['U'])/n]if complete and n else None,
      'total_denominator_metric_role':'confirmed_success_indicator; unknown contributes0 only to this descriptive/sensitivity statistic, never reclassified F',
      'Wilson95_total_denominator':wilson(c['S'],n)if complete else None,
      'SR_valid_denominator':c['S']/valid if complete and valid else None,
      'Wilson95_valid_denominator':wilson(c['S'],valid)if complete else None}
def validate(configs,records):
    cfg={c['configuration_id']:c for c in configs};assert len(cfg)==len(configs)
    expected={};by=defaultdict(dict)
    for c in configs:
        assert c['expected_n']==len(c['cases'])>0
        expected[c['configuration_id']]={x['case_id']:x for x in c['cases']}
        assert len(expected[c['configuration_id']])==c['expected_n']
        assert len({identity(x)for x in c['cases']})==c['expected_n']
        for x in c['cases']:
            assert x['order']in['1234','4321'] and isinstance(x['seed'],int)
            assert x['condition_version']==c['condition_version']
    for r in records:
        cid=r['configuration_id'];case=r['case_id'];assert cid in cfg and case in expected[cid]
        assert case not in by[cid],'Duplicate selected case; attempt selection belongs to the source ledger'
        assert identity(r)==identity(expected[cid][case]) and r['final'] is True
        assert isinstance(r['raw_available'],bool)
        for ref in r['raw_refs']:
            assert isinstance(ref['bytes'],int)and ref['bytes']>=0
            assert len(ref['sha256'])==64 and all(x in'0123456789abcdef'for x in ref['sha256'])
        assert set(r['oracles'])==set(ORACLES)
        for name in ORACLES:
            o=r['oracles'][name];assert o['success']is None or type(o['success'])is bool
            assert set(o['per_k'])==set(map(str,KS))and set(o['per_k'].values())<={'S','F','U'}
            phase=o['phase'];lower=o['observed_phase_lower_bound']
            assert phase is None or type(phase)is int and 0<=phase<=7
            assert lower is None or type(lower)is int and 0<=lower<=7
            if o['success']is not None:assert r['closure_valid']is True and phase is not None
            if o['success']is True:assert phase==7
            if not r['raw_available']:
                assert not r['raw_refs']and o['success']is None and phase is None and lower is None
                assert set(o['per_k'].values())=={'U'}
            else:assert r['raw_refs'],'Available raw requires source SHA references, not summary scores alone'
        by[cid][case]=r
    return cfg,expected,by

def summarize(config,rows):
    n=config['expected_n'];complete=len(rows)==n;out={'configuration_id':config['configuration_id'],'expected_n':n,
      'received_final_n':len(rows),'pending_n':n-len(rows),'complete':complete,'oracles':{}}
    for name in ORACLES:
        values=[r['oracles'][name]for r in rows];whole=['U'if v['success']is None else'S'if v['success']else'F'for v in values]
        valid_phase=[v['phase']for v in values if v['success']is not None]
        observed=[v['observed_phase_lower_bound']for v in values if v['observed_phase_lower_bound']is not None]
        out['oracles'][name]={'whole':counts(whole,n,complete),
          'per_k':{str(k):counts([v['per_k'][str(k)]for v in values],n,complete)for k in KS},
          'mean_phase_valid_closed_only':sum(valid_phase)/len(valid_phase)if complete and valid_phase else None,
          'phase_mean_denominator':len(valid_phase),'phase_hist_valid_closed_only':dict(sorted(Counter(valid_phase).items())),
          'funnel_valid_closed_only':{str(k):sum(p>=k for p in valid_phase)for k in range(8)},
          'phase_known_n':len(observed),'observed_phase_lower_bound_hist':dict(sorted(Counter(observed).items())),
          'observed_phase_lower_bound_mean':sum(observed)/len(observed)if observed else None,
          'observed_lower_bound_funnel':{str(k):{'known_reach_n':sum(p>=k for p in observed),'total_n':n,'phase_known_n':len(observed)}for k in range(8)},
          'prefix7_S_but_whole_not_S_case_ids':[r['case_id']for r in rows if r['oracles'][name]['per_k']['7']=='S'and r['oracles'][name]['success']is not True],
          'funnel_definition':'per_k explicitly reports S/F/U for all stages1..7 with full expected denominator. Valid-closed funnel and observed lower-bound funnel are separate descriptions; unknown phases never filled0.'}
    return out

def paired(left,right,left_rows,right_rows,*,replicates=10000,seed=20261105):
    assert left['family']=='Mem0'and right['family']=='TTC','Pair direction must explicitly be TTC minus Mem0'
    assert left['condition_version']==right['condition_version'],'Different conditions cannot be paired'
    assert left['condition_version']and left['scene_list_hash']and right['scene_list_hash']
    assert left['horizon']==right['horizon']and left['camera']==right['camera']
    assert left['scene_list_hash']==right['scene_list_hash']
    a={identity(r):r for r in left_rows};b={identity(r):r for r in right_rows};keys=sorted(set(a)&set(b));pairs=[(a[k],b[k])for k in keys]
    final=len(left_rows)==left['expected_n']and len(right_rows)==right['expected_n']
    out={'left':left['configuration_id'],'right':right['configuration_id'],'definition':'right TTC minus left Mem0',
      'matched_identity_n':len(keys),'left_unmatched_n':len(set(a)-set(b)),'right_unmatched_n':len(set(b)-set(a)),
      'left_pending_n':left['expected_n']-len(left_rows),'right_pending_n':right['expected_n']-len(right_rows),
      'complete_inputs':final,'oracles':{},'bootstrap':{'replicates':replicates if final and keys else 0,'seed':seed,
        'strata':'original order1234/4321; shared paired indices within each statistic',
        'unknown_in_success_rate':'confirmed-success-indicator/unknown-as-failure sensitivity only; true whole SR difference withheld if any unknown pair; identification bounds and complete-case results also reported',
        'phase_scope':'only pairs with both whole verdicts known and both valid closed phases; unknown phase never filled0'}}
    def boot(items,fn):
        if not final or not items:return {'CI95':None,'valid_replicates':0}
        strata=defaultdict(list)
        for pair in items:strata[pair[0]['order']].append(pair)
        rng=random.Random(seed);values=[]
        for _ in range(replicates):
            sample=[]
            for order in sorted(strata):sample+=rng.choices(strata[order],k=len(strata[order]))
            values.append(fn(sample))
        return interval(values)
    for name in ORACLES:
        known=[(x,y)for x,y in pairs if x['oracles'][name]['success']is not None and y['oracles'][name]['success']is not None]
        phase_fn=lambda ps:sum(y['oracles'][name]['phase']-x['oracles'][name]['phase']for x,y in ps)/len(ps)
        whole_fn=lambda ps:sum(int(y['oracles'][name]['success']is True)-int(x['oracles'][name]['success']is True)for x,y in ps)/len(ps)
        def bounds(items, status):
            if not final or not items:return None
            low=high=0
            for x,y in items:
                sx,sy=status(x),status(y)
                low+=int(sy=='S')-int(sx!='F')
                high+=int(sy!='F')-int(sx=='S')
            return [low/len(items),high/len(items)]
        status=lambda r:'U'if r['oracles'][name]['success']is None else'S'if r['oracles'][name]['success']else'F'
        unknown_n=len(pairs)-len(known)
        body={'phase_paired_n':len(known),'phase_unknown_pair_n':unknown_n,
          'paired_mean_phase_difference':phase_fn(known)if final and known else None,
          'phase_difference_bootstrap':boot(known,phase_fn),
          'whole_unknown_pair_n':unknown_n,
          'whole_SR_total_pair_difference':whole_fn(pairs)if final and pairs else None,
          'whole_SR_bootstrap':boot(pairs,whole_fn),
          'whole_SR_total_pair_metric_role':'confirmed_success_indicator / unknown-as-failure sensitivity; not identified true SR difference when U>0',
          'whole_SR_difference':whole_fn(pairs)if final and pairs and not unknown_n else None,
          'whole_SR_difference_identification_bounds':bounds(pairs,status),
          'whole_SR_complete_case':{'paired_n':len(known),'unknown_pair_n':unknown_n,
             'difference':whole_fn(known)if final and known else None,'bootstrap':boot(known,whole_fn),
             'scope':'both whole verdicts known; selected complete-case subset, not the full matched cohort'},
          'per_k':{}}
        for k in KS:
            key=str(k);fn=lambda ps:sum(int(y['oracles'][name]['per_k'][key]=='S')-int(x['oracles'][name]['per_k'][key]=='S')for x,y in ps)/len(ps)
            eligible=[(x,y)for x,y in pairs if x['oracles'][name]['per_k'][key]!='U'and y['oracles'][name]['per_k'][key]!='U']
            u=len(pairs)-len(eligible)
            body['per_k'][key]={'paired_n':len(pairs),'unknown_pair_n':u,
              'SR_total_pair_difference':fn(pairs)if final and pairs else None,**boot(pairs,fn),
              'metric_role':'confirmed_success_indicator / unknown-as-failure sensitivity',
              'true_SR_difference':fn(pairs)if final and pairs and not u else None,
              'SR_difference_identification_bounds':bounds(pairs,lambda r:r['oracles'][name]['per_k'][key]),
              'complete_case':{'paired_n':len(eligible),'unknown_pair_n':u,'difference':fn(eligible)if final and eligible else None,'bootstrap':boot(eligible,fn)}}
        out['oracles'][name]=body
    return out

def aggregate(manifest,records):
    assert manifest['schema']=='task7_relaxed_rescore_aggregation_manifest.v1'
    assert manifest.get('bootstrap_replicates',10000)==10000
    cfg,expected,by=validate(manifest['configurations'],records)
    rows={cid:list(by[cid].values())for cid in cfg}
    return {'schema':'task7_relaxed_three_oracle_aggregate.v1','epoch':time.time(),'source_only_verdicts':True,
      'new_oracle_or_model_calls':0,'configurations':{cid:summarize(c,rows[cid])for cid,c in cfg.items()},
      'pairs':[paired(cfg[p['left']],cfg[p['right']],rows[p['left']],rows[p['right']],
          replicates=manifest.get('bootstrap_replicates',10000),seed=manifest.get('bootstrap_seed',20261105))for p in manifest.get('pairs',[])],
      'notes':['per_k S/F/U comes directly from the source scorer, never from whole unknown or a prior website score.',
        'SR@7 means observed completion of at least7 phases, distinct from whole terminal success; discrepancies are listed.',
        'Full-N S/N and Wilson describe confirmed-success indicators; U is not F. True SR is partially identified by [S/N,(S+U)/N]. Valid-verdict denominators describe a selected conditional subset.',
        'Missing expected records are pending, not silently replaced with unknown or failure; partial SR/CI is withheld.',
        'Phase means use only oracle-known valid closed cases. Observed prefix lower bounds are a separate diagnostic.',
        'Raw hashes are scorer provenance; this aggregation does not reread raw files or re-establish their custody.']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();m=json.loads(a.manifest.read_bytes());r=json.loads(a.results.read_bytes());out=aggregate(m,r['records'])
    out['sources']={'manifest':{'file':str(a.manifest),'sha256':sha(a.manifest)},'results':{'file':str(a.results),'sha256':sha(a.results)},'aggregation_source_sha256':sha(__file__)}
    a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n');print(json.dumps({'file':str(a.output),'sha256':sha(a.output)}))
