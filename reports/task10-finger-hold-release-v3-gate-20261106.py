"""Measured grasp-only30tick fixed-joint gate. No task labels or oracle input."""
from dataclasses import dataclass
from collections import deque
from math import cos,isfinite,sqrt

@dataclass(frozen=True)
class GateConfig:
    stable_ticks:int=30
    lift_m:float=.015
    relative_translation_range_m:float=.002
    relative_angle_range_rad:float=.05
    minimum_up_cosine:float=.8
    measured_open_mean_rad:float=2.82
    command_open_mean_rad:float=2.90
    cooldown_ticks:int=30
    command_increase_epsilon_rad:float=.03
    gap_increase_epsilon_m:float=.00016
    def __post_init__(self):
        if self.stable_ticks<1 or self.cooldown_ticks<0:raise ValueError('invalid_tick_threshold')
        if not all(isfinite(float(x)) for x in self.__dict__.values()):raise ValueError('nonfinite_gate_config')
        if min(self.lift_m,self.relative_translation_range_m,self.relative_angle_range_rad)<=0:raise ValueError('invalid_spatial_threshold')

@dataclass(frozen=True)
class Sample:
    tick:int
    key:str
    lift_m:float
    thumb_contact:bool
    opposing_contact:bool
    support_contact:bool
    relative_position:tuple
    relative_quaternion_wxyz:tuple
    up_cosine:float
    measured_finger_mean:float
    commanded_finger_mean:float
    finger_gap_m:float=0.

class GraspGate:
    def __init__(self,config):
        self.config=config;self.attached=None;self.last_tick=None
        self.history=deque(maxlen=config.stable_ticks)
        self.last_release_tick=-10**12;self.last_release_reason=None
        self.latched_command=None;self.previous_command=None;self.previous_gap=None;self.latest_bad_pair_older_tick=-10**12
    def release_now(self,tick,reason):
        self.attached=None;self.latched_command=None;self.last_release_tick=tick;self.last_release_reason=reason
        self.history.clear();self.latest_bad_pair_older_tick=-10**12
    def update(self,s):
        vals=[s.lift_m,s.up_cosine,s.measured_finger_mean,s.commanded_finger_mean,s.finger_gap_m,*s.relative_position,*s.relative_quaternion_wxyz]
        if not all(isfinite(float(v)) for v in vals):raise ValueError('nonfinite_grasp_sample')
        if len(s.relative_position)!=3 or len(s.relative_quaternion_wxyz)!=4:raise ValueError('invalid_relative_pose')
        qn=sqrt(sum(x*x for x in s.relative_quaternion_wxyz))
        if abs(qn-1)>.002:raise ValueError('nonunit_relative_quaternion')
        if self.last_tick is not None and s.tick!=self.last_tick+1:raise ValueError('attachment_requires_continuous_native_ticks')
        self.last_tick=s.tick;c=self.config
        prior_command=self.previous_command;prior_gap=self.previous_gap
        self.previous_command=s.commanded_finger_mean;self.previous_gap=s.finger_gap_m
        if self.attached:
            if s.key!=self.attached:return None
            reason=None
            if s.commanded_finger_mean>=c.command_open_mean_rad:reason='policy_opening_command'
            elif self.latched_command is not None and s.commanded_finger_mean>self.latched_command+c.command_increase_epsilon_rad:reason='policy_opening_trend'
            elif prior_gap is not None and s.finger_gap_m>prior_gap+c.gap_increase_epsilon_m:reason='measured_finger_gap_increasing'
            if reason:
                self.release_now(s.tick,reason);return 'release'
            return None
        eligible=(s.key and s.tick>self.last_release_tick+c.cooldown_ticks and s.lift_m>=c.lift_m and
            s.thumb_contact and s.opposing_contact and not s.support_contact and s.up_cosine>=c.minimum_up_cosine and
            s.commanded_finger_mean<c.command_open_mean_rad and s.measured_finger_mean<c.measured_open_mean_rad)
        if not eligible:
            self.history.clear();self.latest_bad_pair_older_tick=-10**12;return None
        if self.history and self.history[-1].key!=s.key:
            self.history.clear();self.latest_bad_pair_older_tick=-10**12
        # Maintain exact pairwise window-diameter failures in O(window) per tick.
        # A bad pair expires when its older endpoint leaves the rolling window.
        oldest=s.tick-c.stable_ticks+1
        for h in self.history:
            if h.tick<oldest:continue
            d2=sum((a-b)**2 for a,b in zip(h.relative_position,s.relative_position))
            dot=abs(sum(a*b for a,b in zip(h.relative_quaternion_wxyz,s.relative_quaternion_wxyz)))
            if d2>c.relative_translation_range_m**2 or min(1.,dot)<cos(c.relative_angle_range_rad/2):
                self.latest_bad_pair_older_tick=max(self.latest_bad_pair_older_tick,h.tick)
        self.history.append(s)
        if len(self.history)<c.stable_ticks or self.latest_bad_pair_older_tick>=oldest:return None
        self.attached=s.key;self.latched_command=max(s.commanded_finger_mean,s.measured_finger_mean);return 'attach'
