import json,hashlib,unittest
from pathlib import Path
P=Path(__file__).parent;A=json.loads((P/'release-segment-review.json').read_text())
class SegmentReview(unittest.TestCase):
 def test_full_contact_boundary_audit(self):
  self.assertEqual(len({c['case_id']for c in A['cases']}),111);self.assertEqual(len(A['cases']),123);self.assertEqual(hashlib.sha256((P/'release-segment-review.py').read_bytes()).hexdigest(),A['rules_sha256'])
 def test_no_touch_or_correct_protocol_can_be_a_wrong_release(self):
  for c in A['cases']:
   if c['max_motion_m']<.02 or c['correct_for_available_source']:self.assertFalse(c['retained_wrong_release'])
 def test_confirmed_false_positive_regression(self):
  c=next(c for c in A['cases']if c['case_id']=='r4_new30_A_s0_h8_030');self.assertFalse(c['retained_wrong_release']);self.assertLess(c['max_motion_m'],.002);self.assertEqual(c['expected_by_protocol'][0]['object'],'A');self.assertEqual(c['expected_by_protocol'][1]['object'],'B')
 def test_published_max_phase_is_bound_to_actual_timeline(self):
  d=json.loads((P/'data.json').read_text())
  for task in ['5','7','10']:
   t=d['tasks'][task]if task=='7'else json.loads((P/('task'+task+'-videos.json')).read_text())
   for c in t['cases']:
    rows=json.loads((P/c['trace']).read_text())['rows'];field='phase11'if task=='5'else'phase13';self.assertEqual(c['max_phase'],max(r[field]for r in rows))
 def test_source_verdicts_not_rewritten(self):
  self.assertTrue(A['source_protocols_and_scores_unchanged']);self.assertEqual([A['counts'][t]['retained_wrong']for t in ['5','7','10']],[4,0,2])
if __name__=='__main__':unittest.main()
