"""Eight interval-end native steps from measured held targets to nominal ABSOLUTE targets.

No joint sign assumptions, opening offsets, task state, or object pose writes.
The joint is removed immediately; this temporary handoff changes motor targets
only and retires after the same8 ticks used by the normal endpoint chain.
"""
import numpy as np

class ReleaseTargetBlend:
 def __init__(self,held,start_tick,transition_ticks=8):
  self.held=np.asarray(held,dtype=np.float32).copy()
  if self.held.shape!=(6,)or not np.isfinite(self.held).all():raise ValueError('invalid_held_targets')
  if transition_ticks!=8:raise ValueError('frozen_native_transition_ticks8')
  self.start_tick=int(start_tick);self.last_tick=self.start_tick;self.transition_ticks=8;self.done=False;self.mode='blend_to_nominal_absolute8_interval_end'
 def apply(self,raw,tick):
  raw=np.asarray(raw,dtype=np.float32);tick=int(tick)
  if raw.shape!=(6,)or not np.isfinite(raw).all():raise ValueError('invalid_nominal_targets')
  if tick<self.last_tick or tick<self.start_tick:raise ValueError('nonmonotonic_native_tick')
  self.last_tick=tick;elapsed=tick-self.start_tick+1
  if elapsed>=self.transition_ticks:self.done=True;return raw.copy()
  alpha=np.float32(elapsed/self.transition_ticks)
  return np.asarray(self.held+alpha*(raw-self.held),dtype=np.float32)
