"""Synthetic schema-only vectors; never published as evaluation/media records.
Run with jsonschema==4.23.0 available (no network or data-file writes).
"""
import copy
import json
import pathlib
import unittest
from jsonschema import Draft202012Validator
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT/'docs/media-manifest-v1.schema.json').read_text())

class NightMediaSchema(unittest.TestCase):
    def setUp(self):
        Draft202012Validator.check_schema(SCHEMA)
        # Use full root validator to resolve local $defs without external fetches.
        self.validator = Draft202012Validator(SCHEMA)
        asset={'url':'https://zenith-a02012413.tos-cn-beijing.volces.com/liyufeng/safelab-public/media-v1/7/test-only/not-published.mp4','sha256':'a'*64,'bytes':1000}
        self.case={'case_id':'LOCAL_SCHEMA_ONLY','task':'7','record':'LOCAL_SCHEMA_ONLY','issue':None,'checkpoint':30000,'horizon':2,'protocol_version':'SafeLab-Eval-v1.4-B','oracle_version':'placement-v14-test-only','evaluation_id':'LOCAL_SCHEMA_ONLY','condition_version':'LOCAL_SCHEMA_ONLY','stage':'diagnostic','scene_id':'0','scene_list_hash':'b'*64,'side':'left','seed':0,'outcome':'fail','max_phase':0,'videos':{'third_person':None,'head':None,'chest':asset},'frame_log':None,'render_config_hash':'c'*64,'timebase':{'fps':15,'video_time_origin_s':0,'log_time_origin_s':0},'subtask_physical_targets':None,'variant':'attach-v6','grasp_attachment':'fixed_joint_v6'}
    def errors(self, case):
        return list(self.validator.iter_errors({'schema_version':'safelab-media-v1','updated_at':'2026-11-06T22:00:00Z','cases':[case]}))
    def test_h2_assisted_and_r1_require_explicit_oracle(self):
        for protocol in ['SafeLab-Eval-v1.4-A','SafeLab-Eval-v1.4-B','SafeLab-Eval-v1.4-r1']:
            with self.subTest(protocol=protocol):
                c={**self.case,'protocol_version':protocol}
                self.assertEqual(self.errors(c),[])
                c.pop('oracle_version')
                self.assertTrue(self.errors(c))
    def test_h30_is_still_legacy_only_and_unknown_horizon_rejected(self):
        self.assertTrue(self.errors({**self.case,'horizon':30}))
        self.assertTrue(self.errors({**self.case,'horizon':3}))
        self.assertEqual(self.errors({**self.case,'horizon':30,'stage':'legacy','protocol_version':'legacy'}),[])
    def test_unknown_revision_is_not_implicitly_accepted(self):
        self.assertTrue(self.errors({**self.case,'protocol_version':'SafeLab-Eval-v1.4-r10'}))
    def test_external_video_boundary_is_not_weakened(self):
        c=copy.deepcopy(self.case);c['videos']['chest']['url']='https://unapproved.invalid/not-published.mp4'
        self.assertTrue(self.errors(c))

if __name__=='__main__': unittest.main()
