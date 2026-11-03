"""Proposed unified executor: all13 joints, interval_end, no clip or velocity ramp.
No physical/asset changes. Diagnostic until expert parity passes.
"""
import math
VERSION='interval-end13-linear-fd-v1.1-r7'
def command(previous,endpoint,substep,dt=1/120,native_steps=8):
    if len(previous)!=13 or len(endpoint)!=13:raise ValueError('13_joint_targets_required')
    if type(substep)is not int or not 1<=substep<=native_steps or dt<=0:raise ValueError('invalid_native_clock')
    if not all(math.isfinite(float(v))for v in [*previous,*endpoint]):raise ValueError('nonfinite_target')
    alpha=substep/native_steps
    q=[float(a)+(float(b)-float(a))*alpha for a,b in zip(previous,endpoint)]
    velocity=[(float(b)-float(a))/(native_steps*dt)for a,b in zip(previous,endpoint)]
    return q,velocity
