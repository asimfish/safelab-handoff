"""Independent ordered prefix-seven physical outcome; no policy feedback."""
from collections import deque
import numpy as np
from scipy.spatial.transform import Rotation

class ObstructionFive:
    def __init__(self,profile,order,origin):
        self.sequence=[('A','temporary_A'),('B','temporary_B'),('C','target_C'),('A','pad_A'),('B','pad_B')]
        self.sources=['pad_A','pad_B','pad_C','temporary_A','temporary_B']
        self.profile=profile;self.origin=np.asarray(origin);self.phase=0
        self.lifted=False;self.history=deque(maxlen=121);self.events=[];self.failure=None;self.last_tick=None

    def observe(self,tick,poses,contacts):
        if self.last_tick is not None and tick!=self.last_tick+1:raise ValueError('physical_evaluator_requires_every_native_tick')
        self.last_tick=tick
        canonical=np.asarray(poses).copy();canonical[:,:3]-=self.origin
        if not np.isfinite(canonical).all():raise ValueError('nonfinite_object_pose')
        if np.any(canonical[:,2]<self.profile['scene']['table_top']-.1):self.failure='object_fell'
        ups=Rotation.from_quat(np.roll(canonical[:,3:],-1,axis=1)).apply(np.tile([0,0,1],(3,1)))[:,2]
        if np.any(ups<.5):self.failure='object_toppled'
        if self.failure or self.phase==5:return self.phase==5 and self.failure is None
        key,target=self.sequence[self.phase];ix='ABC'.index(key)
        source=self.sources[self.phase]
        bottom=self.profile['scene'].get('object_bottom_offsets',{}).get(key,self.profile['scene']['half_height'])
        source_z=self.profile['scene']['supports'][source][2]+bottom
        # Original observed lift threshold: 0.65 of the source pickup height.
        lift=float(self.profile.get('stages',{}).get(str(self.phase+1),{}).get('lift_height',self.profile['motion']['lift_height']))
        if canonical[ix,2]-source_z>=.65*lift:self.lifted=True
        center=np.asarray(self.profile['scene']['supports'][target])+[0,0,bottom]
        target_contacts=[x for x in contacts if x['object']==key]
        support_token='/Balance/' if target=='pan' else '/'+target
        support=any(support_token in x['actor'] and x['contact_count']>0 for x in target_contacts)
        fingers=any('/Robot/' in x['actor'] and '/hand2_' in x['actor'] and x['contact_count']>0 for x in target_contacts)
        placed=np.linalg.norm(canonical[ix,:2]-center[:2])<=.025 and abs(canonical[ix,2]-center[2])<=.012 and ups[ix]>=.97
        if self.lifted and support and not fingers and placed:
            self.history.append(canonical[ix].copy())
        else:self.history.clear()
        if len(self.history)==121:
            h=np.asarray(self.history);drift=np.linalg.norm(h[:,:3]-h[-1,:3],axis=1).max()
            rotations=Rotation.from_quat(np.roll(h[:,3:],-1,axis=1))
            angle=(rotations[-1].inv()*rotations).magnitude().max()
            if drift<=.001 and angle<=.02:
                self.events.append({'phase':self.phase+1,'tick':tick,'object':key,'target':target,
                    'stable_ticks':121,'drift_m':float(drift),'rotation_range_rad':float(angle),
                    'position':canonical[ix,:3].tolist(),'support_contact':True,'right_hand_contact':False})
                self.phase+=1;self.lifted=False;self.history.clear()
        if self.phase==5:
            # Every other beaker must still be upright on its own original pad.
            for k in 'ABC':
                if k==key:continue
                j='ABC'.index(k);target_end={'A':'pad_A','B':'pad_B','C':'target_C'}[k];bottom_k=self.profile['scene']['object_bottom_offsets'][k];c=np.asarray(self.profile['scene']['supports'][target_end])+[0,0,bottom_k]
                if np.linalg.norm(canonical[j,:2]-c[:2])>.025 or abs(canonical[j,2]-c[2])>.012 or ups[j]<.97:
                    self.failure='other_beaker_not_restored'
            return self.failure is None
        return False
