"""Single-factor diagnostic, never a replacement formal controller.
Changes only hand6 velocity feed-forward to the recorded native zero value.
Arm finite differences, positions, gains, gravity and scene remain unchanged.
"""
from pathlib import Path
import json
VERSION='diagnostic-armFD-handFFzero-r7'
def install(native):
 initial=native.initial_gate;dump=native.dump;receipt={'intervention':VERSION,'changed_calls':0,'max_removed_hand_velocity_rad_s':0.,'formal_eligible':False}
 def setup(owner,deadline):
  result=initial(owner,deadline);view=owner.views[0];robot=view.robot;original=robot.set_joint_velocity_target;ordered=[int(x)for x in view.arm_ids+view.hand_ids]
  def setter(target,*args,**kwargs):
   ids=kwargs.get('joint_ids',args[0]if args else None)
   if ids is not None and [int(x)for x in ids]==ordered:
    assert target.shape[-1]==13
    receipt['max_removed_hand_velocity_rad_s']=max(receipt['max_removed_hand_velocity_rad_s'],float(target[...,7:].abs().max().item()));target=target.clone();target[...,7:]=0;receipt['changed_calls']+=1
   return original(target,*args,**kwargs)
  robot.set_joint_velocity_target=setter
  return result
 def emit(path,value):
  if Path(path).name in ['RESULT.json','NATIVE_CONTROLLER.json']:
   value=dict(value);value['requested_base_replay_mode']=value.get('mode','endpoint_linear8_ff13');value['controller_protocol']=VERSION;value['single_factor_intervention']=dict(receipt);value['formal_eligible']=False
  return dump(path,value)
 native.initial_gate=setup;native.dump=emit
