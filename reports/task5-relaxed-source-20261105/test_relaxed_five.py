import sys
from pathlib import Path
import unittest
import numpy as np
from relaxed_five import score,SEQUENCE

OLD=Path('/home/liyufeng/ops/safelab_5b_stable_attach_20261101/eval_v1_pipeline_20261103')
if OLD.is_dir():
    sys.path.insert(0,str(OLD));from placement_five_v11 import evaluate as frozen_v11
    sys.path.insert(0,str(OLD/'round5/common_FD/task5_oracles'))
    from obstruction_outcome import ObstructionFive
else:
    from placement_five_v11 import evaluate as frozen_v11
    from obstruction_outcome import ObstructionFive

PROFILE={'scene':{'table_top':1.,'half_height':.05,'object_bottom_offsets':dict.fromkeys('ABC',.05),
 'supports':{'pad_A':[-.2,0,1.],'pad_B':[0,0,1.],'pad_C':[.2,0,1.],
 'temporary_A':[-.2,.2,1.],'temporary_B':[0,.2,1.],'target_C':[.2,.2,1.]}},'motion':{'lift_height':.1}}

def fixture(hold=130):
    current=np.array([PROFILE['scene']['supports']['pad_'+k]+[.05,1,0,0,0] for k in 'ABC'])
    # supports above are xyz; build center z explicitly rather than an extra coordinate.
    current=np.array([PROFILE['scene']['supports']['pad_'+k]+[1,0,0,0] for k in 'ABC'],dtype=np.float32)
    current[:,2]+=.05;frames=[current.copy() for _ in range(5)];spans=[]
    for key,target in SEQUENCE:
        ix='ABC'.index(key);lift=current.copy();lift[ix,2]+=.1;frames.extend([lift.copy(),lift.copy()])
        start=len(frames);current[ix,:3]=np.array(PROFILE['scene']['supports'][target])+[0,0,.05]
        frames.extend([current.copy() for _ in range(hold)]);spans.append((start,len(frames),ix))
    n=len(frames)
    return [np.array(frames),np.ones((n,5),bool),np.ones((n,3),bool),np.ones((n,3),bool),np.arange(n),spans]

def run(f):return score(PROFILE,*f[:5])

class Tests(unittest.TestCase):
    def test_native_reference_full_sequence(self):
        f=fixture();a=run(f)
        self.assertTrue(all(r['success'] and r['phase']==5 for r in a.values()))
        old=frozen_v11(PROFILE,f[0],f[1],f[2],f[4])
        self.assertEqual(a['placement_v1_1']['phase'],old['phase'])
        self.assertEqual([r['tick']for r in a['placement_v1_1']['events']],[r['tick']for r in old['events']])
        strict=ObstructionFive(PROFILE,'forward',[0,0,0])
        for tick,p in zip(f[4],f[0]):
            strict.observe(int(tick),p,[{'object':k,'actor':'/'+target,'contact_count':1}for k,target in SEQUENCE])
        self.assertEqual(a['strict_v1']['events'],[{**r,'index':r['tick']}for r in a['strict_v1']['events']])
        self.assertEqual([r['tick']for r in a['strict_v1']['events']],[r['tick']for r in strict.events])

    def test_relaxed_region_pose_height_and_12_ticks(self):
        f=fixture(12);angle=.4
        for start,end,ix in f[5]:
            f[0][start:end,ix,0]+=.04;f[0][start:end,ix,2]+=.008
            f[0][start:end,ix,3:]=[np.cos(angle/2),np.sin(angle/2),0,0]
        f[1][:]=False
        self.assertTrue(run(f)['placement_v1_2_relaxed']['success'])
        self.assertFalse(run(f)['placement_v1_1']['success'])

    def test_11_ticks_are_insufficient(self):
        f=fixture(11);end=f[5][0][1]
        f[:5]=[x[:end]for x in f[:5]]
        self.assertEqual(run(f)['placement_v1_2_relaxed']['phase'],0)

    def test_initial_target_is_not_completion(self):
        f=fixture();f[0][:]=f[0][-1]
        self.assertEqual(run(f)['placement_v1_2_relaxed']['phase'],0)

    def test_five_each_held_tilted_and_outside(self):
        for kind in ['held','tilted','outside']:
            for i in range(5):
                with self.subTest(kind=kind,index=i):
                    f=fixture();start,end,ix=f[5][0];f[:5]=[x[:end]for x in f[:5]]
                    if kind=='held':f[2][start:end,ix]=False
                    elif kind=='outside':f[0][start:end,ix,0]+=.051+.001*i
                    else:
                        angle=.46+.01*i;f[0][start:end,ix,3:]=[np.cos(angle/2),np.sin(angle/2),0,0]
                    self.assertEqual(run(f)['placement_v1_2_relaxed']['phase'],0)

    def test_completed_sequence_not_revoked_by_later_fall(self):
        f=fixture();f[0][-1,2,2]=.7
        a=run(f)['placement_v1_2_relaxed'];self.assertTrue(a['success']);self.assertTrue(a['fall_after_place'])
        self.assertFalse(run(f)['placement_v1_1']['success'])

    def test_original_catastrophic_active_object_guard(self):
        f=fixture();start,end,ix=f[5][0];f[0][start:end,ix,3:]=[.5,np.sqrt(.75),0,0]
        self.assertEqual(run(f)['placement_v1_2_relaxed']['phase'],0)

    def test_missing_physical_ticks_rejected(self):
        f=fixture();f[4][3:]+=1
        with self.assertRaises(ValueError):run(f)

if __name__=='__main__':unittest.main(verbosity=2)
