"""Test-only verdict fixtures. These are never an actual rescoring catalog."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from aggregate_cases import aggregate,validate,paired,ORACLES,KS

def config(cid='M',family='Mem0',n=2):
    return {'configuration_id':cid,'family':family,'expected_n':n,'condition_version':'fixture-only-original',
      'horizon':8,'camera':'chest','scene_list_hash':'sha256:'+'a'*64,
      'cases':[{'case_id':str(i),'scene_id':'scene'+str(i),'seed':739000+i,'order':'1234'if i%2==0 else'4321','condition_version':'fixture-only-original'}for i in range(n)]}
def row(c,i,phase=2,success=False):
    x={'configuration_id':c['configuration_id'],**c['cases'][i],'final':True,'closure_valid':True,'raw_available':True,
       'raw_refs':[{'file':'/test-only/not-an-actual-raw-file','bytes':1,'sha256':'a'*64}],'oracles':{}}
    for name in ORACLES:x['oracles'][name]={'success':success,'phase':phase,'observed_phase_lower_bound':phase,'per_k':{str(k):'S'if phase>=k else'F'for k in KS}}
    return x
def manifest(cs,pairs=None):return {'schema':'task7_relaxed_rescore_aggregation_manifest.v1','configurations':cs,'pairs':pairs or[]}

class Tests(unittest.TestCase):
    def test_whole_unknown_preserves_explicit_prefix_S_and_total_denominator(self):
        c=config();a=row(c,0);b=row(c,1)
        for o in b['oracles'].values():o.update(success=None,phase=None,observed_phase_lower_bound=4,per_k={str(k):'S'if k<=4 else'U'for k in KS})
        x=aggregate(manifest([c]),[a,b])['configurations']['M']['oracles']['strict']
        self.assertEqual((x['whole']['F'],x['whole']['U'],x['whole']['total_n']),(1,1,2))
        self.assertIsNone(x['whole']['complete_verdict_SR'])
        self.assertEqual(x['per_k']['4']['S'],1);self.assertEqual(x['per_k']['4']['SR_total_denominator'],.5)
        self.assertEqual(x['mean_phase_valid_closed_only'],2);self.assertEqual(x['phase_mean_denominator'],1)
        self.assertEqual(x['phase_known_n'],2);self.assertEqual(x['observed_lower_bound_funnel']['4']['known_reach_n'],1)
        self.assertGreater(x['whole']['Wilson95_total_denominator']['high'],0)

    def test_prefix7_is_not_whole_terminal_success(self):
        c=config(n=1);r=row(c,0,7,False);x=aggregate(manifest([c]),[r])['configurations']['M']['oracles']['v1.1']
        self.assertEqual(x['whole']['S'],0);self.assertEqual(x['per_k']['7']['S'],1)
        self.assertEqual(x['prefix7_S_but_whole_not_S_case_ids'],['0'])

    def test_missing_raw_requires_all_U_and_all_unknown_mean_is_null(self):
        c=config();rs=[row(c,i)for i in range(2)]
        for r in rs:
            r.update(raw_available=False,closure_valid=False,raw_refs=[])
            for o in r['oracles'].values():o.update(success=None,phase=None,observed_phase_lower_bound=None,per_k={str(k):'U'for k in KS})
        x=aggregate(manifest([c]),rs)['configurations']['M']['oracles']['relaxed']
        self.assertEqual(x['whole']['U'],2);self.assertEqual(x['whole']['SR_total_denominator'],0)
        self.assertIsNone(x['whole']['SR_valid_denominator']);self.assertIsNone(x['mean_phase_valid_closed_only'])
        self.assertEqual(x['phase_hist_valid_closed_only'],{});self.assertEqual(x['phase_known_n'],0)
        rs[0]['oracles']['relaxed']['per_k']['1']='S'
        with self.assertRaises(AssertionError):validate([c],rs)

    def test_partial_has_pending_not_fabricated_unknown_and_no_SR(self):
        c=config();x=aggregate(manifest([c]),[row(c,0)])['configurations']['M']
        self.assertFalse(x['complete']);self.assertEqual(x['pending_n'],1)
        self.assertEqual(x['oracles']['strict']['whole']['U'],0)
        self.assertIsNone(x['oracles']['strict']['whole']['SR_total_denominator'])
        self.assertIsNone(x['oracles']['strict']['per_k']['1']['Wilson95_total_denominator'])

    def test_pair_excludes_different_seed_and_refuses_different_condition(self):
        a=config(n=1);b=config('T','TTC',1);b['cases'][0]['seed']+=1
        x=paired(a,b,[row(a,0)],[row(b,0)])
        self.assertEqual(x['matched_identity_n'],0);self.assertEqual(x['left_unmatched_n'],1)
        self.assertIsNone(x['oracles']['strict']['paired_mean_phase_difference'])
        b['condition_version']='different'
        with self.assertRaises(AssertionError):paired(a,b,[row(a,0)],[row(b,0)])

    def test_paired_10000_fixed_delta_and_order_strata(self):
        a=config(n=4);b=config('T','TTC',4);rs=[row(a,i,2)for i in range(4)]+[row(b,i,3)for i in range(4)]
        x=aggregate(manifest([a,b],[{'left':'M','right':'T'}]),rs)['pairs'][0]
        self.assertEqual(x['bootstrap']['replicates'],10000);self.assertEqual(x['matched_identity_n'],4)
        for o in x['oracles'].values():
            self.assertEqual(o['phase_paired_n'],4);self.assertEqual(o['paired_mean_phase_difference'],1)
            self.assertEqual(o['phase_difference_bootstrap']['CI95'],[1,1]);self.assertEqual(o['whole_SR_bootstrap']['CI95'],[0,0])

    def test_censored_pairs_never_identify_true_zero_SR_difference(self):
        a=config(n=2);b=config('T','TTC',2);ar=[row(a,i)for i in range(2)];br=[row(b,i)for i in range(2)]
        for o in br[1]['oracles'].values():o.update(success=None,phase=None,observed_phase_lower_bound=6,per_k={str(k):'S'if k<=6 else'U'for k in KS})
        x=aggregate(manifest([a,b],[{'left':'M','right':'T'}]),ar+br)['pairs'][0]['oracles']['strict']
        self.assertEqual(x['whole_SR_total_pair_difference'],0)
        self.assertEqual(x['whole_SR_bootstrap']['CI95'],[0,0])
        self.assertIsNone(x['whole_SR_difference'])
        self.assertEqual(x['whole_SR_difference_identification_bounds'],[0,.5])
        self.assertEqual(x['whole_SR_complete_case']['paired_n'],1)
        self.assertEqual(x['whole_SR_complete_case']['unknown_pair_n'],1)
        self.assertEqual(set(x['per_k']),set(map(str,range(1,8))))
        self.assertEqual(x['per_k']['5']['true_SR_difference'],.5)
        self.assertIsNone(x['per_k']['7']['true_SR_difference'])

    def test_duplicate_selected_case_is_refused(self):
        c=config(n=1);r=row(c,0)
        with self.assertRaises(AssertionError):aggregate(manifest([c]),[r,copy.deepcopy(r)])

    def test_actual_CLI_json_roundtrip_and_immutable_output(self):
        c=config(n=1);r=row(c,0)
        with tempfile.TemporaryDirectory(prefix='task7-relaxed-test-only-')as tmp:
            p=Path(tmp);(p/'manifest.json').write_text(json.dumps(manifest([c])));(p/'records.json').write_text(json.dumps({'test_only':True,'records':[r]}))
            argv=[sys.executable,'-B',str(Path(__file__).with_name('aggregate_cases.py')),'--manifest',str(p/'manifest.json'),'--results',str(p/'records.json'),'--output',str(p/'out.json')]
            run=subprocess.run(argv,capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stderr)
            out=json.loads((p/'out.json').read_text());self.assertEqual(out['new_oracle_or_model_calls'],0)
            self.assertEqual(out['configurations']['M']['oracles']['strict']['mean_phase_valid_closed_only'],2)
            self.assertNotEqual(subprocess.run(argv,capture_output=True,text=True).returncode,0)

if __name__=='__main__':unittest.main(verbosity=2)
