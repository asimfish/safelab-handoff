from pathlib import Path
import json,unittest,hashlib
P=Path(__file__).parent
D=json.loads((P/'task7-diagnostics.json').read_text());A=json.loads((P/'diagnostic-audit.json').read_text());M=json.loads((P/'diagnostic-media.json').read_text())['cases']
class TestRefinement(unittest.TestCase):
 def test_parent_counts_conserved(self):
  self.assertEqual([sum(D['counts'][m].values())for m in ['mem0_30k','ours_aligned_30k','pi05_40k']],[66,40,11]);self.assertEqual(sum(r.get('known',False)for r in D['cases']),285)
 def test_20_independent_checks_and_coverage(self):
  self.assertTrue(A['passed']);self.assertEqual(len(A['cases']),20);self.assertTrue(all(r['passed']for r in A['cases']));all_groups={(r['method'],r['subclass'])for r in D['cases']if r.get('subclass')};self.assertEqual(all_groups,{(r['method'],r['subclass'])for r in A['cases']})
 def test_trace_integrity_and_exact_events(self):
  by={r['case_id']:r for r in D['cases']}
  for c in M:
   b=(P/c['trace']).read_bytes();self.assertEqual(hashlib.sha256(b).hexdigest(),c['trace_sha256']);j=json.loads(b);self.assertEqual(j['case_id'],c['case_id']);self.assertEqual(j['sampling']['retained_rows'],len(j['rows']));self.assertTrue(set(j['sampling']['phase_event_ticks'])<={r['tick']for r in j['rows']});self.assertEqual(max(r['phase13']for r in j['rows']),len(by[c['case_id']]['weighed_objects']))
 def test_media_and_independent_raw_binding(self):
  a={r['case_id']:r for r in A['cases']};self.assertEqual(len({c['case_id']for c in M}),20);self.assertEqual(set(a),{c['case_id']for c in M})
  for c in M:
   self.assertEqual(c['raw_sha256'],a[c['case_id']]['raw_sha256']);self.assertTrue(c['video']['PUT_GET_SHA_verified']);self.assertTrue(2_000_000<=c['video']['bytes']<=8_000_000);self.assertTrue(c['video']['url'].startswith('https://zenith-a02012413.tos-cn-beijing.volces.com/liyufeng/safelab-public/videos-v1/long_tasks_20261106/7/repair_v2/'))
 def test_rules_hashes_and_no_order_failure(self):
  self.assertEqual(hashlib.sha256((P/'diagnostic_rules.py').read_bytes()).hexdigest(),D['rules_sha256']);self.assertEqual(hashlib.sha256((P/'diagnostic_audit.py').read_bytes()).hexdigest(),A['audit_script_sha256']);self.assertFalse(any(r.get('subclass')=='wrong_object'for r in D['cases']));self.assertTrue(all(r['v11_order_deviation_is_not_v13_failure']for r in D['cases']if r.get('known')))
 def test_prior_source_data_unchanged(self):self.assertEqual(hashlib.sha256(json.dumps(json.loads((P/'data.json').read_text())['tasks']['7'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'96c9847c77df19ae27bed638b88b48a6754f4a52bf9a095d55711e9301877b67')
if __name__=='__main__':unittest.main()
