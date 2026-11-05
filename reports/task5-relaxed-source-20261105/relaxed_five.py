"""CPU-only parameterized, ordered five-task placement scoring.

Existing strict/v1.1 sources remain immutable. Poses use world wxyz, 120Hz.
No model, controller, scene or renderer is imported by this module.
"""
from pathlib import Path
import json
import numpy as np
from scipy.spatial.transform import Rotation

PARAMETERS = json.loads((Path(__file__).parent/'FROZEN_PARAMETERS.json').read_text())
SEQUENCE = [('A','temporary_A'),('B','temporary_B'),('C','target_C'),('A','pad_A'),('B','pad_B')]
SOURCES = ['pad_A','pad_B','pad_C','temporary_A','temporary_B']


def _first_run(mask, length, start, stop):
    """First ending index of a wholly valid window in [start, stop)."""
    if stop-start < length:
        return None
    m=mask[start:stop]
    invalid=np.r_[0,np.cumsum(~m)]
    ends=np.flatnonzero(invalid[length:]-invalid[:-length]==0)
    return start+int(ends[0])+length-1 if len(ends) else None


def score(profile, poses, supports, clear, no_fingers, ticks, *, origin=(0,0,0)):
    p=np.asarray(poses,dtype=np.float32).copy()
    t=np.asarray(ticks,dtype=np.int64)
    if p.ndim!=3 or p.shape[1:]!=(3,7) or not len(p) or not np.isfinite(p).all():
        raise ValueError('finite nonempty [ticks,3,7] poses required')
    if len(t)!=len(p) or np.any(np.diff(t)!=1):
        raise ValueError('complete consecutive 120Hz physical ticks required')
    p[:,:,:3]-=np.asarray(origin)
    n=len(p)
    supports=np.asarray(supports,dtype=bool);clear=np.asarray(clear,dtype=bool)
    no_fingers=np.asarray(no_fingers,dtype=bool)
    if supports.shape!=(n,5) or clear.shape!=(n,3) or no_fingers.shape!=(n,3):
        raise ValueError('contact arrays do not match physical ticks')
    rotations=Rotation.from_quat(np.roll(p[:,:,3:].astype(float).reshape(-1,4),-1,axis=1))
    up=rotations.apply(np.tile([0,0,1],(n*3,1)))[:,2].reshape(n,3)
    bad=(p[:,:,2]<profile['scene']['table_top']-.1)|(up<.5)
    bad_any=np.flatnonzero(bad.any(axis=1))
    original_stop=int(bad_any[0]) if len(bad_any) else n

    def centers(ix,target):
        key='ABC'[ix]
        bottom=profile['scene'].get('object_bottom_offsets',{}).get(key,profile['scene']['half_height'])
        return np.asarray(profile['scene']['supports'][target])+[0,0,bottom]

    def geometry(phase,xy,upright,height,strict=False):
        key,target=SEQUENCE[phase];ix='ABC'.index(key);c=centers(ix,target)
        mask=(np.linalg.norm(p[:,ix,:2]-c[:2],axis=1)<=xy)&(up[:,ix]>=upright)
        if strict:
            return mask&(np.abs(p[:,ix,2]-c[2])<=height)&supports[:,phase]&no_fingers[:,ix]
        return mask&clear[:,ix]&(supports[:,phase]|(np.abs(p[:,ix,2]-c[2])<=height))

    answers={}
    for metric in ['strict_v1','placement_v1_1','placement_v1_2_relaxed']:
        strict=metric=='strict_v1';relaxed=metric=='placement_v1_2_relaxed'
        xy=PARAMETERS['xy_tolerance_m'] if relaxed else .025
        upright=PARAMETERS['upright_cos_min'] if relaxed else .97
        height=PARAMETERS['rest_height_tolerance_m'] if relaxed else .012 if strict else .005
        window=PARAMETERS['debounce_ticks'] if relaxed else 121 if strict else 30
        start=0;events=[];ever_placed=set();first_placed={}
        for phase,(key,target) in enumerate(SEQUENCE):
            ix='ABC'.index(key)
            if relaxed:
                # Previously placed, inactive objects cannot revoke a completed
                # stage. Preserve original catastrophic guard for active or
                # not-yet-placed objects. This ambiguity is frozen in parameters.
                guarded=[j for j in range(3) if j==ix or j not in ever_placed]
                fail=np.flatnonzero(bad[start:,guarded].any(axis=1))
                stop=start+int(fail[0]) if len(fail) else n
            else:
                stop=original_stop
            if start>=stop:
                break
            source_z=centers(ix,SOURCES[phase])[2]
            lift=float(profile.get('stages',{}).get(str(phase+1),{}).get('lift_height',profile['motion']['lift_height']))
            lifted=np.flatnonzero(p[start:stop,ix,2]-source_z>=.65*lift)
            if not len(lifted):
                break
            first_lift=start+int(lifted[0])
            mask=geometry(phase,xy,upright,height,strict)
            search=first_lift
            at=None
            while search<stop:
                candidate=_first_run(mask,window,search,stop)
                if candidate is None:
                    break
                if not strict:
                    at=candidate;break
                h=p[candidate-window+1:candidate+1,ix]
                drift=np.linalg.norm(h[:,:3]-h[-1,:3],axis=1).max()
                rot=Rotation.from_quat(np.roll(h[:,3:].astype(float),-1,axis=1))
                angle=(rot[-1].inv()*rot).magnitude().max()
                if drift<=.001 and angle<=.02:
                    at=candidate;break
                # Advance the ending window by one, preserving source semantics.
                search=candidate-window+2
            if at is None:
                break
            events.append({'phase':phase+1,'tick':int(t[at]),'index':at,'object':key,'target':target})
            ever_placed.add(ix);first_placed.setdefault(ix,at);start=at+1
        success=len(events)==5
        if not relaxed:
            success=success and original_stop==n
        if success and not relaxed:
            if strict:
                # Frozen strict source validates the other A/C objects when B
                # completes; no final no-contact gate is invented.
                at=events[-1]['index']
                for ix,target in [(0,'pad_A'),(2,'target_C')]:
                    c=centers(ix,target)
                    success=success and bool(np.linalg.norm(p[at,ix,:2]-c[:2])<=.025 and abs(p[at,ix,2]-c[2])<=.012 and up[at,ix]>=.97)
            else:
                success=all(bool(geometry(slot,.025,.97,.005)[-1]) for slot in [3,4,2])
        fall_objects=[]
        for ix,at in first_placed.items():
            after=np.flatnonzero(bad[at+1:,ix])
            if len(after):fall_objects.append({'object':'ABC'[ix],'first_tick':int(t[at+1+int(after[0])])})
        answers[metric]={'success':bool(success),'phase':len(events),'events':events,'fall_after_place':bool(fall_objects),'fall_after_place_objects':fall_objects}
    return answers
