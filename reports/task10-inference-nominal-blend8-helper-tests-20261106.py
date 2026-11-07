import unittest
import numpy as np
from release_target_blend import ReleaseTargetBlend

class BlendTests(unittest.TestCase):
 def test_first_motor_target_is_one_eighth_interval_step(self):
  held=np.array([1.54,2.58,2.43,2.79,2.76,.48],np.float32);x=ReleaseTargetBlend(held,100);np.testing.assert_array_equal(x.apply(np.ones(6,dtype=np.float32),100),held+np.float32(.125)*(np.ones(6,dtype=np.float32)-held))
 def test_eighth_interval_end_tick_is_exact_nominal_absolute_target(self):
  raw=np.array([1.52,2.335,2.335,2.5,2.5,.5],np.float32);x=ReleaseTargetBlend([1.54,2.58,2.43,2.79,2.76,.48],100);np.testing.assert_array_equal(x.apply(raw,107),raw);self.assertTrue(x.done)
 def test_recorded_closed_command_is_not_remapped_to_opening(self):
  held=np.array([1.54,2.58,2.43,2.79,2.76,.48],np.float32);raw=np.array([1.52,2.335,2.335,2.5,2.5,.5],np.float32);x=ReleaseTargetBlend(held,100);last=held.copy()
  for t in range(100,108):
   out=x.apply(raw,t);self.assertTrue(np.all(out[1:3]<=last[1:3]+1e-7));self.assertLessEqual(float(np.max(np.abs(out-last))),float(np.max(np.abs(raw-held)))/8+1e-6);last=out
 def test_full_opening_remains_opening(self):
  x=ReleaseTargetBlend([1.54,2.5,2.5,2.7,2.7,.5],10);raw=np.array([1.0,3.1,3.1,3.0,3.0,.7],np.float32);out=x.apply(raw,17);np.testing.assert_array_equal(out,raw)
 def test_current_raw_target_used_during_transition(self):
  held=np.full(6,2.5,np.float32);x=ReleaseTargetBlend(held,0);a=x.apply(np.full(6,2.3,np.float32),2);b=x.apply(np.full(6,2.9,np.float32),4);np.testing.assert_allclose(a,2.425);np.testing.assert_allclose(b,2.75)
 def test_no_input_mutation_and_no_cross_lane_state(self):
  held=np.full(6,2.5,np.float32);raw=np.full(6,2.3,np.float32);before=raw.copy();a=ReleaseTargetBlend(held,0);b=ReleaseTargetBlend(np.full(6,2.7,np.float32),0);a.apply(raw,4);np.testing.assert_array_equal(raw,before);np.testing.assert_array_equal(held,np.full(6,2.5,np.float32));np.testing.assert_allclose(b.apply(raw,0),np.full(6,2.65,np.float32))
 def test_invalid_shape_and_nan_rejected(self):
  with self.assertRaises(ValueError):ReleaseTargetBlend([0]*5,0)
  x=ReleaseTargetBlend([0]*6,0)
  with self.assertRaises(ValueError):x.apply([float('nan')]*6,1)
 def test_time_reversal_rejected(self):
  x=ReleaseTargetBlend([0]*6,10);x.apply([0]*6,12)
  with self.assertRaises(ValueError):x.apply([0]*6,11)
if __name__=='__main__':unittest.main()
