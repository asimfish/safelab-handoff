import copy,unittest
from aggregate_history_math import aggregate

def row(case='test_only',available=True,unknown=False):
 return {'case_id':case,'variant':'mem0_30k','checkpoint':30000,'horizon':8,'condition':'test_only_not_actual','raw_SHA_verified':available,'strict_original':{'success':False},'math_protocols':{n:{'verdict':'U'if unknown else'F','phase':None if unknown else 2,'observed_phase_lower_bound':4 if unknown and available else None if unknown else 2,'censored':unknown and available,'per_k':{str(k):'S'if available and k<=(4 if unknown else 2)else'U'if unknown else'F'for k in range(1,8)},'fall_after_place_objects':0}for n in ['v1.1','v1.2-relaxed']}}
class Tests(unittest.TestCase):
 def test_math_success_does_not_promote_canonical_coverage(self):
  r=row();r['math_protocols']['v1.2-relaxed'].update(verdict='S',phase=7,observed_phase_lower_bound=7,per_k={str(k):'S'for k in range(1,8)})
  g=aggregate([r])[0];self.assertEqual(g['math']['v1.2-relaxed']['S'],1);self.assertEqual(g['canonical_placement_relaxed'],{'S':0,'F':0,'U':1});self.assertIsNone(g['formal_placement_success'])
 def test_censored_prefix_and_full_denominator_are_retained(self):
  g=aggregate([row('f'),row('c',unknown=True)])[0];m=g['math']['v1.2-relaxed'];self.assertEqual((m['S'],m['F'],m['U'],m['N']),(0,1,1,2));self.assertIsNone(m['complete_verdict_SR']);self.assertEqual(m['mean_phase_valid_closed_only'],2);self.assertEqual(m['mean_phase_n'],1);self.assertEqual(m['per_stage']['4']['S'],1);self.assertEqual(m['per_stage']['5']['U'],1)
 def test_missing_raw_is_not_a_zero_phase_or_a_fabricated_planned_trial(self):
  g=aggregate([row(available=False,unknown=True)])[0];m=g['math']['v1.1'];self.assertEqual(g['n_actual_historical_cases'],1);self.assertEqual(m['N'],1);self.assertIsNone(m['mean_phase_valid_closed_only']);self.assertEqual(m['mean_phase_n'],0);self.assertEqual(m['observed_phase_known_n'],0);self.assertTrue(all(x['U']==1 for x in m['per_stage'].values()))
if __name__=='__main__':unittest.main(verbosity=2)
