import unittest
import numpy as np
from release_target_floor import ReleaseTargetFloor

class ReleaseFloorTests(unittest.TestCase):
    def setUp(self):
        self.held=np.array([1.554,2.50,2.51,2.52,2.53,1.52],np.float32)
        self.raw=np.array([1.52,2.335,2.345,2.355,2.365,1.52],np.float32)
    def test_first_released_tick_is_continuous(self):
        f=ReleaseTargetFloor(self.held,self.raw,100)
        np.testing.assert_array_equal(f.apply(self.raw,100),self.held)
    def test_flexion_cannot_close_through_grasp_during_opening(self):
        f=ReleaseTargetFloor(self.held,self.raw,100)
        for t in range(100,140):
            out=f.apply(self.raw,t)
            self.assertTrue(np.all(out[1:5]>=self.held[1:5]))
            self.assertLessEqual(out[0],self.held[0])
        self.assertFalse(f.done)
    def test_raw_signal_not_mutated(self):
        before=self.raw.copy();f=ReleaseTargetFloor(self.held,self.raw,100);f.apply(self.raw,101)
        np.testing.assert_array_equal(before,self.raw)
    def test_normal_opening_catches_up_and_passthrough(self):
        target=self.held.copy();target[0]-=.04;target[1:5]=3.14
        f=ReleaseTargetFloor(self.held,target,100)
        for t in range(100,109):out=f.apply(target,t)
        self.assertTrue(f.done);np.testing.assert_array_equal(out,target)
    def test_constant_thumb_does_not_immediately_end_floor(self):
        f=ReleaseTargetFloor(self.held,self.raw,100)
        for t in range(100,120):f.apply(self.raw,t)
        self.assertEqual(f.mode,'opening')
    def test_sub30mrad_noise_keeps_floor(self):
        f=ReleaseTargetFloor(self.held,self.raw,100)
        for t in range(100,120):
            x=self.raw.copy();x[1:3]-=.01*(t%2);f.apply(x,t)
        self.assertEqual(f.mode,'opening')
    def test_intended_closing_releases_floor_smoothly(self):
        f=ReleaseTargetFloor(self.held,self.raw,100)
        for t in range(100,109):f.apply(self.raw,t)
        x=self.raw.copy();x[1:5]-=.08;previous=f.last.copy()
        np.testing.assert_array_equal(f.apply(x,109),previous)
        for t in range(110,118):out=f.apply(x,t)
        self.assertTrue(f.done);np.testing.assert_array_equal(out,x)
    def test_unassigned_thumb_axis_restores_over_eight_ticks(self):
        held=self.held.copy();held[5]+=.08;f=ReleaseTargetFloor(held,self.raw,100)
        a=f.apply(self.raw,100);b=f.apply(self.raw,104);c=f.apply(self.raw,108)
        self.assertEqual(a[5],held[5]);self.assertAlmostEqual(float(b[5]),float((held[5]+self.raw[5])/2),places=6);self.assertEqual(c[5],self.raw[5])
    def test_two_lanes_have_private_state(self):
        a=ReleaseTargetFloor(self.held,self.raw,100);b=ReleaseTargetFloor(self.held,self.raw,100);x=self.raw.copy();x[1:3]-=.08;a.apply(x,101)
        self.assertEqual(a.mode,'closing_restore');self.assertEqual(b.mode,'opening')
    def test_small_policy_opening_opens_actual_fingers_before_raw_catches_measured(self):
        anchor=self.raw.copy();anchor[1:5]-=.035
        f=ReleaseTargetFloor(self.held,self.raw,100,raw_at_latch=anchor)
        for t in range(100,109):out=f.apply(self.raw,t)
        self.assertTrue(np.all(out[1:5]>self.held[1:5]))
        self.assertTrue(np.all(out[1:5]<2.9))
    def test_open_reference_removes_reference_offset(self):
        anchor=self.raw.copy();f=ReleaseTargetFloor(self.held,self.raw,100,raw_at_latch=anchor)
        target=self.raw.copy();target[1:5]=2.9
        for t in range(100,109):out=f.apply(target,t)
        self.assertTrue(f.done);np.testing.assert_array_equal(out,target)
    def test_nonfinite_rejected(self):
        x=self.raw.copy();x[1]=np.nan
        with self.assertRaises(AssertionError):ReleaseTargetFloor(self.held,x,100)

if __name__=='__main__':unittest.main()
