import json,math,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from task10_fd_velocities_20261104 import fd_velocities

def main():
 checks=[]
 rng=np.random.default_rng(721);ticks=np.arange(101);times=np.cumsum(rng.uniform(.003,.02,101));x=np.zeros((101,5,7));x[...,3]=1
 x[...,:3]=times[:,None,None]*np.array([.1,-.2,.3])[None,None,:]
 angles=times*.73;q=Rotation.from_rotvec(angles[:,None]*np.array([1.,2.,3.])[None,:]/np.sqrt(14)).as_quat()
 x[...,3:]=np.roll(q,1,axis=-1)[:,None,:];x[1::2,:,3:]*=-1
 got=fd_velocities(ticks,x,times)
 assert np.max(np.abs(got['linear_velocity']-[.1,-.2,.3]))<1e-12
 assert np.max(np.abs(got['angular_speed']-.73))<1e-12;checks+=['variable_actual_dt','constant_axis_quaternion_reference','double_cover']
 expected=Rotation.from_quat(np.roll(x[1:,:,3:],-1,axis=-1).reshape(-1,4))*Rotation.from_quat(np.roll(x[:-1,:,3:],-1,axis=-1).reshape(-1,4)).inv()
 np.testing.assert_allclose(got['angular_velocity'].reshape(-1,3),expected.as_rotvec()/np.repeat(np.diff(times),5)[:,None],rtol=1e-11,atol=1e-12)
 static=np.zeros((5,2,7));static[...,3]=1;static[1::2,:,3:]*=-1
 d=fd_velocities(np.arange(5),static,verified_fixed_dt=1/120)
 assert np.max(np.abs(d['linear_speed']))==0 and np.max(np.abs(d['angular_speed']))==0;checks+=['static_pose','fixed_dt_source_explicit','first_tick_omitted']
 for tt,xx,kw in [(np.array([1,3,4,5,6]),static,{'verified_fixed_dt':1/120}),(np.arange(5),static,{}),(np.arange(5),static,{'times':np.array([0,1,1,2,3])})]:
  try:fd_velocities(tt,xx,**kw)
  except ValueError:pass
  else:raise AssertionError('invalid native clock silently accepted')
 checks+=['missing_native_tick_rejected','implicit_dt_rejected','nonpositive_dt_rejected']
 # Independent axes at every tick verify noncommuting rotations, including sign flips.
 random_pose=np.zeros((37,3,7));rot=Rotation.random(111,random_state=rng)
 random_pose[...,3:]=np.roll(rot.as_quat().reshape(37,3,4),1,axis=-1)
 random_pose[::2,:,3:]*=-1
 clock=np.cumsum(rng.uniform(.005,.02,37))
 rr=fd_velocities(np.arange(37),random_pose,clock)
 ref=Rotation.from_quat(np.roll(random_pose[1:,:,3:],-1,axis=-1).reshape(-1,4))*Rotation.from_quat(np.roll(random_pose[:-1,:,3:],-1,axis=-1).reshape(-1,4)).inv()
 err=rr['angular_velocity'].reshape(-1,3)-ref.as_rotvec()/np.repeat(np.diff(clock),3)[:,None]
 np.testing.assert_allclose(err,0,atol=2e-10,rtol=0)
 checks+=['random_noncommuting_rotations_scipy_crosscheck']
 return {'passed':True,'checks':checks,'max_angular_error_rad_s':float(np.max(np.abs(got['angular_speed']-.73))),'scipy_rotvec_crosscheck':True,'CPU_only':True,'GPU_used':False}
if __name__=='__main__':
 result=main();p=Path(__file__).parent/'FD_TESTS.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
