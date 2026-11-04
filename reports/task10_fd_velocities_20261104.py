"""CPU-only dense native-tick pose differencing. Quaternion input order: wxyz."""
import numpy as np

def fd_velocities(ticks, poses, times=None, *, verified_fixed_dt=None):
    ticks=np.asarray(ticks);x=np.asarray(poses,dtype=np.float64)
    if ticks.ndim!=1 or len(ticks)<2 or not np.issubdtype(ticks.dtype,np.integer):raise ValueError('integer_native_tick_sequence_required')
    if not np.all(np.diff(ticks)==1):raise ValueError('missing_or_duplicate_native_tick')
    if x.shape[0]!=len(ticks) or x.shape[-1]!=7 or not np.isfinite(x).all():raise ValueError('invalid_native_pose')
    if times is None:
        if verified_fixed_dt is None or not np.isfinite(verified_fixed_dt) or verified_fixed_dt<=0:raise ValueError('actual_timestamp_or_verified_fixed_physics_dt_required')
        dt=np.full(len(ticks)-1,float(verified_fixed_dt));time_source='consecutive_native_tick * verified SCENE_CONTRACT.dt'
    else:
        t=np.asarray(times,dtype=np.float64)
        if t.shape!=ticks.shape or not np.isfinite(t).all() or not np.all(np.diff(t)>0):raise ValueError('invalid_physics_time')
        dt=np.diff(t);time_source='recorded_per_physics_tick_time'
    q=x[...,3:].copy();norm=np.linalg.norm(q,axis=-1,keepdims=True)
    if np.any(norm<1e-12):raise ValueError('zero_quaternion')
    q/=norm;a=q[1:].copy();b=q[:-1]
    a*=np.where(np.sum(a*b,axis=-1,keepdims=True)<0,-1.,1.)
    # q_t tensor_product inverse(q_previous), world-frame relative rotation.
    aw,av=a[...,:1],a[...,1:];bw,bv=b[...,:1],-b[...,1:]
    rw=aw*bw-np.sum(av*bv,axis=-1,keepdims=True)
    rv=aw*bv+bw*av+np.cross(av,bv)
    mag=np.linalg.norm(rv,axis=-1,keepdims=True)
    angle=2*np.arctan2(mag,np.clip(rw,0.,1.))
    scale=np.divide(angle,mag,out=np.full_like(mag,2.),where=mag>1e-14)
    shape=(len(dt),)+(1,)*(x.ndim-1);den=dt.reshape(shape)
    linear=np.diff(x[...,:3],axis=0)/den
    angular=(rv*scale)/den
    return {'ticks':ticks[1:],'linear_velocity':linear,'angular_velocity':angular,
            'linear_speed':np.linalg.norm(linear,axis=-1),'angular_speed':np.linalg.norm(angular,axis=-1),
            'time_source':time_source,'first_tick_velocity':'undefined; omitted, never zero-filled'}
