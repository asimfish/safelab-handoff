from pathlib import Path
import unittest,json,hashlib
P=Path(__file__).parent;T=json.loads((P/'task5-videos.json').read_text())
class Task5(unittest.TestCase):
 def test_six_populations(self):
  self.assertEqual(len(T['groups']),6)
  for g in T['groups']:self.assertEqual(sum(v for v in g['failure_counts'].values()if v is not None)+g.get('release_review_count',0),100);self.assertIsNone(g['success13'])
  self.assertEqual(sum(g['failure_counts'].get('unknown',0)for g in T['groups']),31)
 def test_media_and_unpublished(self):
  self.assertEqual(len(T['cases'])+len(T['withheld_release_diagnosis_cases']),53)
  for c in T['cases']:
   b=(P/c['trace']).read_bytes();self.assertEqual(hashlib.sha256(b).hexdigest(),c['trace_sha256']);j=json.loads(b);self.assertTrue(all(r['phase13']is None for r in j['rows']));self.assertEqual(c['source_input_camera'],'third_person');self.assertEqual(c['verdict13'],'unpublished');self.assertTrue(c['video']['PUT_GET_SHA_verified'])
 def test_independent(self):
  a=json.loads((P/'task5-independent-checks.json').read_text());self.assertTrue(a['passed']);self.assertEqual(len(a['sample_checks']),20);self.assertEqual(a['raw_verified'],569)
if __name__=='__main__':unittest.main()
