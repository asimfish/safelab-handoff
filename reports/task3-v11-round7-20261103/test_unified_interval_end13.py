import unittest
from unified_interval_end13 import command
class Tests(unittest.TestCase):
 def test_endpoint(self):self.assertEqual(command([0.]*13,[1.]*13,8)[0],[1.]*13)
 def test_first_tick(self):self.assertEqual(command([0.]*13,[1.]*13,1)[0],[.125]*13)
 def test_finite_difference(self):
  previous=[0.]*13
  for j in range(1,9):
   q,v=command([0.]*13,[1.]*13,j)
   for a,b,c in zip(q,previous,v):self.assertAlmostEqual((a-b)*120,c)
   previous=q
 def test_hand_same_as_arm(self):self.assertEqual(command([0.]*13,[.1]*13,1)[1],[1.5]*13)
 def test_no_clip_or_ramp(self):self.assertEqual(command([0.]*13,[1.]*13,1)[1],command([0.]*13,[1.]*13,8)[1])
 def test_stationary(self):self.assertEqual(command([.3]*13,[.3]*13,4)[1],[0.]*13)
 def test_bad_clock(self):
  with self.assertRaises(ValueError):command([0.]*13,[1.]*13,0)
 def test_bad_target(self):
  with self.assertRaises(ValueError):command([0.]*13,[float('nan')]*13,1)
if __name__=='__main__':unittest.main()
