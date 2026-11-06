from pathlib import Path
import unittest,json,hashlib
P=Path(__file__).parent;T=json.loads((P/'task10-videos.json').read_text())
class Task10(unittest.TestCase):
 def test_all_eight_populations(self):
  self.assertEqual(len(T['groups']),8)
  for g in T['groups']:self.assertEqual(sum(g['failure_counts'].values()),100)
  self.assertEqual(sum(g['failure_counts'].get('unknown',0)for g in T['groups']),55)
 def test_media_sha_and_phase(self):
  self.assertEqual(len(T['cases']),54)
  for c in T['cases']:
   b=(P/c['trace']).read_bytes();self.assertEqual(hashlib.sha256(b).hexdigest(),c['trace_sha256']);j=json.loads(b);self.assertEqual(j['case_id'],c['case_id']);self.assertTrue(c['video']['PUT_GET_SHA_verified']);self.assertTrue(2_000_000<=c['video']['bytes']<=8_000_000)
   if c['verdict13']=='S':self.assertEqual(j['rows'][-1]['phase13'],5)
 def test_audit_and_missing(self):
  a=json.loads((P/'task10-independent-checks.json').read_text());self.assertTrue(a['passed']);self.assertEqual(len(a['sample_checks']),20);self.assertEqual(len(T['pending']),9);self.assertIn('诊断重评分',T['note'])
if __name__=='__main__':unittest.main()
