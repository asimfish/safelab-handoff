"""Frozen Task10 v1.2-relaxed; original v1.1 stays untouched."""
import hashlib,json,math
from pathlib import Path
from base_place_v11 import PlaceTen
ROOT=Path(__file__).resolve().parent
PARAMETERS_SHA256='297cd35b4a169c4c4290b67a7a01f2712cdc41109cde96242ead251eaaf9f527'
_blob=(ROOT/'parameters.json').read_bytes()
assert hashlib.sha256(_blob).hexdigest()==PARAMETERS_SHA256
PARAMETERS=json.loads(_blob)
KEYS='ABCDE'

class RelaxedTen(PlaceTen):
    def __init__(self,profile,order,origin):
        super().__init__(profile,order,origin)
        self.settings=PARAMETERS['placement']
        self.restored=set()
        self.fall_after_place=set()
        self.fall_after_place_events=[]
        self.completed_tick=None

    def predicate(self,ix,target,poses,contacts,attached,ups):
        p=poses[ix];c=self.supports[target];b=self.bottom[ix]
        ox,oy,oz=self.origin;s=self.settings
        if (p[0]-ox-c[0])**2+(p[1]-oy-c[1])**2>s['xy_tolerance_m']**2 or ups[ix]<s['upright_cos_min'] or KEYS[ix]in attached:
            return False
        obj=[e for e in contacts if e['object']==KEYS[ix]and e['contact_count']>0]
        if any('/Robot/'in e['actor']for e in obj):return False
        token='/Balance/'if target=='pan'else'/'+target
        return any(token in e['actor']for e in obj)or abs(p[2]-oz-c[2]-b)<=s['height_fallback_m']

    def observe(self,row):
        tick=row['tick'];poses=row['poses'];contacts=row['contacts'];attached=row.get('attached_keys',[])
        if self.last_tick is not None and tick!=self.last_tick+1:raise ValueError('missing_native_tick')
        if len(poses)!=5 or any(len(p)!=7 or not all(math.isfinite(x)for x in p)for p in poses):raise ValueError('invalid_pose')
        self.last_tick=tick
        if self._initial_z is None:self._initial_z=[p[2]-self.origin[2]for p in poses]
        ups=[1-2*(p[4]*p[4]+p[5]*p[5])/sum(q*q for q in p[3:])for p in poses]
        fell=[i for i,p in enumerate(poses)if p[2]-self.origin[2]<self.floor]
        toppled=[i for i,u in enumerate(ups)if u<.5]
        for i in set(fell+toppled):
            k=KEYS[i]
            if k in self.restored and k not in self.fall_after_place:
                self.fall_after_place.add(k)
                self.fall_after_place_events.append({'object':k,'tick':tick,'phase':self.phase,'reason':'fell'if i in fell else'toppled'})
        # Preserve historical all-object early termination; do not invent future ticks.
        if fell:self.failure='object_fell'
        if toppled:self.failure='object_toppled'
        if self.phase<10 and self.failure is None:
            ix,target=self.sequence[self.phase]
            source='pad_'+KEYS[ix]if target=='pan'else'pan'
            source_z=self.supports[source][2]+self.bottom[ix]
            lift=.025 if source=='pan'else self.profile['motion']['lift_height']
            z=poses[ix][2]-self.origin[2]
            self._phase_min_z=z if self._phase_min_z is None else min(self._phase_min_z,z)
            if self._initial_z[ix]>=source_z+.65*lift:
                self.guard_triggered_phases.add(self.phase)
                self._guard_contact_seen=self._guard_contact_seen or any(e['object']==KEYS[ix]and e['contact_count']>0 and'/Robot/'in e['actor']for e in contacts)
                if self._guard_contact_seen and z-max(source_z,self._phase_min_z)>=.65*lift:self.lifted=True
            elif z-source_z>=.65*lift:self.lifted=True
            self.count=self.count+1 if self.lifted and self.predicate(ix,target,poses,contacts,attached,ups)else 0
            if self.count>=self.settings['debounce_ticks_120hz']:
                self.events.append({'phase':self.phase+1,'tick':tick,'object':KEYS[ix],'target':target,'placement_ticks':self.settings['debounce_ticks_120hz']})
                if target=='pad_'+KEYS[ix]:self.restored.add(KEYS[ix])
                self.phase+=1;self.count=0;self.lifted=False;self._phase_min_z=None;self._guard_contact_seen=False
                if self.phase==10:self.completed_tick=tick
        self.final_ok=self.phase==10
        return self.final_ok
