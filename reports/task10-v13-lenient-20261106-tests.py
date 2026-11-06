import copy, unittest
import importlib.util
from pathlib import Path
_spec=importlib.util.spec_from_file_location('task10_v13',Path(__file__).with_name('task10-v13-lenient-20261106-oracle.py'))
_mod=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_mod)
LenientObjects=_mod.LenientObjects


class FrozenProtocolTests(unittest.TestCase):
    def setUp(self):
        pads={f'pad_{k}':[0,i*.12,0] for i,k in enumerate('ABCDE')}
        self.profile={'scene':{'supports':{**pads,'pan':[.3,.24,.1]},'half_height':.04,'table_top':0}}
        self.row={'tick':125,'poses':[[0,i*.12,.04,1,0,0,0] for i in range(5)],'contacts':[],'attached_keys':[]}

    def test_initial_pads_are_zero(self):
        o=LenientObjects(self.profile);o.observe(self.row)
        self.assertEqual(o.phase,0);self.assertFalse(o.final_ok)
        self.assertAlmostEqual(o.xy,.055)

    def test_weigh_then_return_and_cup_order_free(self):
        o=LenientObjects(self.profile);r=copy.deepcopy(self.row)
        for index in [4,2,0,3,1]:
            r['poses'][index]=[.3,.24,.14,1,0,0,0];o.observe(r);r['tick']+=1
            r['poses'][index]=[0,index*.12,.04,1,0,0,0];o.observe(r);r['tick']+=1
        self.assertEqual(o.phase,5);self.assertTrue(o.final_ok)

    def test_held_lift_and_air_reject_even_near_xy(self):
        r=copy.deepcopy(self.row);r['poses'][0][2]=.08
        o=LenientObjects(self.profile);self.assertFalse(o.predicate(0,'pad_A',r))
        r['contacts']=[{'object':'A','actor':'/Robot/hand','contact_count':1}]
        self.assertFalse(o.predicate(0,'pad_A',r))
        r['contacts'].append({'object':'A','actor':'/Scene/pad_A','contact_count':1})
        self.assertFalse(o.predicate(0,'pad_A',r))

    def test_robot_touch_at_surface_allowed(self):
        r=copy.deepcopy(self.row);r['contacts']=[{'object':'A','actor':'/Robot/hand','contact_count':1}]
        self.assertTrue(LenientObjects(self.profile).predicate(0,'pad_A',r))

    def test_wrong_pad_and_return_without_weigh_reject(self):
        r=copy.deepcopy(self.row);r['poses'][0][1]=.12
        o=LenientObjects(self.profile);self.assertFalse(o.predicate(0,'pad_A',r))
        o.observe(r);self.assertEqual(o.phase,0)

    def test_no_revocation_after_completed(self):
        o=LenientObjects(self.profile);r=copy.deepcopy(self.row)
        r['poses'][0]=[.3,.24,.14,1,0,0,0];o.observe(r)
        r['tick']+=1;r['poses'][0]=[0,0,.04,1,0,0,0];o.observe(r)
        r['tick']+=1;r['poses'][0]=[0,0,.04,.5,.866025403784,0,0];o.observe(r)
        self.assertEqual(o.phase,1)


if __name__=='__main__':unittest.main()
