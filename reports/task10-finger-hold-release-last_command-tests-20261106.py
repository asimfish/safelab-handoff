from pathlib import Path
import ast
import dataclasses
import sys
import types
import unittest

import numpy as np
import torch

ROOT = Path(sys.argv[1])
OLD = Path(sys.argv[2])
sys.argv = [sys.argv[0]]
sys.path.insert(0, str(ROOT / 'actor_mem0_original'))
from physx_attachment import PhysXAttachment
import grasp_gate as gg

IDS = [1, 3, 5, 7, 9, 11, 13, 19, 20, 21, 22, 23, 29]
HAND = IDS[7:]


class Robot:
    def set_joint_position_target(self, target):
        self.target = target.clone()


class ReleaseTests(unittest.TestCase):
    def fixture(self, count=1):
        q = torch.zeros((count, 36), dtype=torch.float32)
        q[:, IDS] = torch.tensor([.2, -.64, 1.5, -.8, -.3, -1., -.36,
                                  1.519176959, 2.3033061, 2.3033061, 2.5, 2.5, .5])
        value = PhysXAttachment.__new__(PhysXAttachment)
        value.scene = types.SimpleNamespace(command=q, ids=IDS, hand_ids=HAND, robot=Robot())
        value.config = types.SimpleNamespace(command_open_mean_rad=2.9, command_increase_epsilon_rad=.03)
        value.active = [{'commanded_open_mean': 2.3033061, 'raw_thumb_command': 1.519176959,
                         'finger_q': np.array([1.538731456, 2.576589108, 2.426136494, 2.79, 2.76, .4788], np.float32)}] + [None] * (count - 1)
        value.previous_raw_command = None
        value.reasons = []
        def release(i, reason):
            value.active[i] = None
            value.reasons.append(reason)
        value._release = release
        return value

    def test_latch_preserves_the_previous_motor_target(self):
        a=self.fixture();raw=a.scene.command.clone()
        a.active[0]['finger_q']=raw[0,HAND].numpy().copy()
        a.before_step()
        self.assertTrue(torch.equal(a.scene.robot.target,raw))
        self.assertTrue(torch.equal(a.scene.command,raw))

    def test_measured_hold_would_introduce_a_motor_target_jump(self):
        a=self.fixture();raw=a.scene.command.clone();a.before_step()
        self.assertGreater(abs(float(a.scene.robot.target[0,IDS[8:10]].mean()-raw[0,IDS[8:10]].mean())),.19)

    def test_opening_restores_a_more_open_target_than_the_frozen_target(self):
        a=self.fixture();held=a.scene.command[0,HAND].numpy().copy();a.active[0]['finger_q']=held
        a.scene.command[:,IDS[8:10]]=2.335261345;a.before_step()
        self.assertIsNone(a.active[0])
        self.assertGreater(float(a.scene.robot.target[0,IDS[8:10]].mean()),float(held[1:3].mean())+.03)

    def test_closing_command_while_latched_cannot_increase_clamp_target(self):
        a=self.fixture();held=a.scene.command[0,HAND].numpy().copy();a.active[0]['finger_q']=held
        a.scene.command[:,IDS[8:10]]=2.0;a.before_step()
        self.assertIsNotNone(a.active[0])
        self.assertTrue(np.array_equal(a.scene.robot.target[0,HAND].numpy(),held))

    def test_real_absolute_opposing_opening_releases_same_tick(self):
        a = self.fixture()
        a.scene.command[:, IDS[8:10]] = 2.55
        a.before_step()
        self.assertIsNone(a.active[0])
        self.assertTrue(torch.equal(a.scene.robot.target, a.scene.command))

    def test_constant_nominal_thumb_with_tracking_error_does_not_release(self):
        a=self.fixture();a.active[0]['finger_q']=a.scene.command[0,HAND].numpy().copy()
        a.before_step();self.assertIsNotNone(a.active[0])

    def test_thumb_opening_relative_to_frozen_motor_target_releases(self):
        a=self.fixture();a.active[0]['finger_q']=a.scene.command[0,HAND].numpy().copy()
        a.scene.command[:,IDS[7]]-=.04;a.before_step();self.assertIsNone(a.active[0])

    def test_other_dofs_and_inactive_lanes_are_unmodified(self):
        a = self.fixture(2)
        raw = a.scene.command.clone()
        a.before_step()
        self.assertTrue(torch.equal(a.scene.robot.target[1], raw[1]))
        other = [i for i in range(36) if i not in HAND]
        self.assertTrue(torch.equal(a.scene.robot.target[0, other], raw[0, other]))

    def test_after_step_gate_uses_the_same_latched_command_reference(self):
        classes = [c for c in vars(gg).values() if isinstance(c, type) and c.__module__ == gg.__name__]
        Gate = next(c for c in classes if hasattr(c, 'update') and hasattr(c, 'release_now'))
        Config = next(c for c in classes if dataclasses.is_dataclass(c) and 'stable_ticks' in c.__dataclass_fields__)
        Sample = next(c for c in classes if dataclasses.is_dataclass(c) and 'measured_finger_mean' in c.__dataclass_fields__)
        gate = Gate(Config())
        def sample(tick, command):
            return Sample(tick=tick, key='A', lift_m=.04, thumb_contact=True, opposing_contact=True,
                          support_contact=False, relative_position=(.05, 0, .12),
                          relative_quaternion_wxyz=(1, 0, 0, 0), up_cosine=1,
                          measured_finger_mean=2.5, commanded_finger_mean=command, finger_gap_m=.075)
        for tick in range(1, 31):
            result = gate.update(sample(tick, 2.3))
        self.assertEqual(result, 'attach')
        self.assertIsNone(gate.update(sample(31, 2.30)))
        self.assertEqual(gate.update(sample(32, 2.34)), 'release')


if __name__ == '__main__':
    unittest.main(verbosity=2)
