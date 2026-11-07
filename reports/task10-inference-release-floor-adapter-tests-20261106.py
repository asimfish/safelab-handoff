"""Exercise the actual adapter with recorded motor/measurement mismatch values."""
from pathlib import Path
import sys,types,unittest
from unittest.mock import patch
import numpy as np
import torch
ROOT=Path(sys.argv.pop(1));sys.path.insert(0,str(ROOT/'actor_mem0_original'))
from physx_attachment import PhysXAttachment
IDS=[1,3,5,7,9,11,13,19,20,21,22,23,29];HAND=IDS[7:]
class Robot:
 def set_joint_position_target(self,x):self.target=x.clone()
class AdapterTests(unittest.TestCase):
 def make(self,count=1):
  q=torch.zeros((count,36),dtype=torch.float32);q[:,IDS]=torch.tensor([.2,-.64,1.5,-.8,-.3,-1.,-.36,1.519176959,2.3033061,2.3033061,2.5,2.5,.5]);a=PhysXAttachment.__new__(PhysXAttachment);a.scene=types.SimpleNamespace(count=count,command=q,ids=IDS,hand_ids=HAND,robot=Robot(),tick_count=100);a.config=types.SimpleNamespace(command_open_mean_rad=2.9,command_increase_epsilon_rad=.03);a.active=[{'key':'A','joint':'/attachment','tick':50,'commanded_open_mean':2.3033061,'raw_thumb_command':1.519176959,'raw_finger_command_at_latch':q[0,HAND].numpy().copy(),'finger_q':np.array([1.538731456,2.576589108,2.426136494,2.79,2.76,.4788],np.float32)}]+[None]*(count-1);a.previous_raw_command=None;a.release_floors=[None]*count;a.pending_release_drives=[None]*count;a.gap_digits=[2]*count;a.gates=[types.SimpleNamespace(release_now=lambda *x:None)for _ in range(count)];a.precision=types.SimpleNamespace(disable=lambda *x:None);a.events=[];a._event=lambda e:a.events.append(e);a.removed=[];a.stage=types.SimpleNamespace(RemovePrim=lambda path:a.removed.append(path),GetPrimAtPath=lambda path:False);return a
 def step(self,a):
  with patch.dict(sys.modules,{'pxr':types.SimpleNamespace(UsdPhysics=types.SimpleNamespace())}):a.before_step()
 def test_real_release_has_no_closing_snap(self):
  a=self.make();held=a.active[0]['finger_q'].copy();a.scene.command[0,IDS[8:10]]=2.335261345;raw=a.scene.command.clone();self.step(a);self.assertIsNone(a.active[0]);np.testing.assert_array_equal(a.scene.robot.target[0,HAND].numpy(),held);self.assertEqual(a.removed,['/attachment']);self.assertTrue(torch.equal(raw,a.scene.command))
 def test_small_nominal_opening_opens_actual_opposing_fingers(self):
  a=self.make();held=a.active[0]['finger_q'].copy();a.scene.command[0,IDS[8:10]]=2.335261345
  for t in range(100,109):a.scene.tick_count=t;self.step(a)
  out=a.scene.robot.target[0,HAND].numpy();self.assertGreater(out[1],held[1]);self.assertGreater(out[2],held[2]);self.assertTrue(any(e['event']=='release_drive_floor_start'for e in a.events))
 def test_constant_thumb_is_not_false_release(self):
  a=self.make();self.step(a);self.assertIsNotNone(a.active[0]);self.assertEqual(a.removed,[])
 def test_arm_unused_dofs_and_other_lane_unchanged(self):
  a=self.make(2);a.scene.command[0,IDS[8:10]]=2.335261345;raw=a.scene.command.clone();self.step(a);other=[i for i in range(36)if i not in HAND];self.assertTrue(torch.equal(a.scene.robot.target[0,other],raw[0,other]));self.assertTrue(torch.equal(a.scene.robot.target[1],raw[1]))
 def test_actual_handoff_record_is_created(self):
  a=self.make();a.scene.command[0,IDS[8:10]]=2.335261345;self.step(a);pending=a.pending_release_drives[0];self.assertIsNotNone(pending);np.testing.assert_array_equal(np.asarray(pending['expected_finger_targets_rad'],np.float32),a.scene.robot.target[0,HAND].numpy());self.assertEqual(pending['tick'],100)
if __name__=='__main__':unittest.main()
