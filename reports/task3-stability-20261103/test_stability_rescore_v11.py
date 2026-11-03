import copy,unittest
from stability_rescore_v11 import Window
TH={'position_range_m':.002,'rotation_range_rad':.02}
def row(t):
 o={'support_contact_points':{'rack_S1':1,'rack_S2':1},'robot_contact_points':0,'link_position_world_m':[0,0,.04],'bottom_world_z_m':0,'tilt_deg':0,'hand_clearance_m':1,'hand_origin_clearance_m':1,'quaternion_world_wxyz':[1,0,0,0],'angular_velocity_rad_s':[.12,0,0],'linear_velocity_m_s':[0,0,0]}
 return {'tick':t,'objects':{'A':copy.deepcopy(o),'B':copy.deepcopy(o)},'supports':{'rack_S1':{'center_world_m':[0,0,0]},'rack_S2':{'center_world_m':[0,0,0]}},'liquid_counts':{'B':100,'total':100}}
class StabilityTests(unittest.TestCase):
 def test_no_double_hold_and_noise(self):
  w=Window(TH)
  for t in range(360):
   r=row(t);w.push(r,2);self.assertFalse(w.restore(r,None))
  r=row(360);w.push(r,2);self.assertTrue(w.restore(r,None))
 def test_sliding(self):
  w=Window(TH)
  for t in range(361):
   r=row(t);r['objects']['A']['link_position_world_m'][0]=t*.00001;w.push(r,2)
  self.assertFalse(w.restore(r,None))
 def test_quaternion_sign(self):
  w=Window(TH)
  for t in range(361):
   r=row(t);r['objects']['A']['quaternion_world_wxyz']=[(-1)**t,0,0,0];w.push(r,2)
  self.assertTrue(w.restore(r,None))
 def test_contact_resets_window(self):
  w=Window(TH)
  for t in range(361):
   r=row(t)
   if t==100:r['objects']['A']['robot_contact_points']=1
   w.push(r,2)
  self.assertFalse(w.restore(r,None))
 def test_tilt_rejected(self):
  w=Window(TH)
  for t in range(361):
   r=row(t);r['objects']['A']['tilt_deg']=20;w.push(r,2)
  self.assertFalse(w.restore(r,None))
if __name__=='__main__':unittest.main()
