import numpy as np
class EndpointSlew:
    """One causal per-lane endpoint filter, no oracle or object state input."""
    def __init__(self, initial_command, parameters):
        self.p=np.asarray(initial_command,dtype=np.float32).copy()
        self.v=np.zeros(13,dtype=np.float64)
        self.dt=1.0/float(parameters['Hz'])
        self.vmax=np.asarray(parameters['velocity_limit_rad_s'],dtype=float)
        self.amax=np.asarray(parameters['acceleration_limit_rad_s2'],dtype=float)
        if self.p.shape!=(13,) or not np.isfinite(self.p).all():raise ValueError('invalid_initial13')
        if self.vmax.shape!=(13,) or self.amax.shape!=(13,) or np.any(self.vmax<=0) or np.any(self.amax<=0):raise ValueError('invalid_slew_limits')
        self.clamped_frames=0
    def step(self, endpoint):
        target=np.asarray(endpoint,dtype=np.float32)
        if target.shape!=(13,) or not np.isfinite(target).all():raise ValueError('nonfinite_or_invalid_endpoint13')
        wanted=(target.astype(float)-self.p.astype(float))/self.dt
        lo=np.maximum(-self.vmax,self.v-self.amax*self.dt)
        hi=np.minimum(self.vmax,self.v+self.amax*self.dt)
        if np.all(wanted>=lo) and np.all(wanted<=hi):
            delivered=target.copy()
        else:
            velocity=np.clip(wanted,lo,hi)
            delivered=(self.p.astype(float)+velocity*self.dt).astype(np.float32)
            self.clamped_frames+=1
        self.v=(delivered.astype(float)-self.p.astype(float))/self.dt
        self.p=delivered.copy()
        return delivered
