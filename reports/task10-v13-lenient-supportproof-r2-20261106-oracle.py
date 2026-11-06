"""SafeLab v1.3 geometry and unordered-object Task10 scoring, no simulator dependency.

Confirmed user interpretation: each beaker must visit the balance, THEN its own
pad; order between beakers is unrestricted. Five completed objects, not ten
ordered target events. Initial pad occupancy is never completion.
"""
import math


class LenientObjects:
    def __init__(self, profile, origin=(0, 0, 0), keys='ABCDE'):
        self.keys = keys
        self.origin = origin
        scene = profile['scene']
        self.supports = scene['supports']
        self.bottom = [scene.get('object_bottom_offsets', {}).get(k, scene['half_height']) for k in keys]
        centers = list(self.supports.values())
        self.min_target_spacing = min(math.dist(a[:2], b[:2]) for i, a in enumerate(centers) for b in centers[i+1:])
        self.xy = min(.075, round(self.min_target_spacing, 12)/2 - .005)
        if self.xy <= 0:
            raise ValueError('targets_too_close_for_frozen_rule')
        self.weighed = {}
        self.completed = {}
        self.events = []
        self.last_tick = None
        self.failure = None
        self.floor = scene['table_top'] - .1

    def predicate(self, index, target, row):
        pose = row['poses'][index]
        x, y, z = (pose[i] - self.origin[i] for i in range(3))
        norm = sum(q*q for q in pose[3:])
        if norm <= 0 or not all(math.isfinite(v) for v in pose):
            raise ValueError('invalid_pose')
        up = 1 - 2*(pose[4]**2 + pose[5]**2)/norm
        center = self.supports[target]
        d2 = (x-center[0])**2 + (y-center[1])**2
        if d2 > self.xy**2 or up < .8:
            return False
        distances = {k: (x-c[0])**2+(y-c[1])**2 for k, c in self.supports.items()}
        if any(d < d2-1e-12 or (k != target and abs(d-d2) <= 1e-12) for k, d in distances.items()):
            return False
        contacts = [e for e in row['contacts'] if e['object'] == self.keys[index] and e['contact_count'] > 0]
        token = '/Balance/' if target == 'pan' else '/' + target
        supported = any(token in e['actor'] for e in contacts)
        height = abs(z-center[2]-self.bottom[index])
        held = self.keys[index] in row.get('attached_keys', ()) or any('/Robot/' in e['actor'] for e in contacts)
        # Robot contact is allowed only with actual target support. Height
        # proximity alone cannot qualify a held/attached airborne object.
        if held and (not supported or height > .015):
            return False
        return supported or height <= .015

    def observe(self, row):
        tick = row['tick']
        if self.last_tick is not None and tick != self.last_tick+1:
            raise ValueError('missing_native_tick')
        self.last_tick = tick
        if len(row['poses']) != len(self.keys):
            raise ValueError('wrong_object_count')
        for p in row['poses']:
            if len(p) != 7 or not all(math.isfinite(x) for x in p) or sum(q*q for q in p[3:]) <= 0:
                raise ValueError('invalid_pose')
        if any(p[2]-self.origin[2] < self.floor for p in row['poses']):
            self.failure = 'object_fell'
        if any(1-2*(p[4]**2+p[5]**2)/sum(q*q for q in p[3:]) < .5 for p in row['poses']):
            self.failure = 'object_toppled'
        if self.failure is None:
            for i, key in enumerate(self.keys):
                if key in self.completed:
                    continue
                if key not in self.weighed and self.predicate(i, 'pan', row):
                    self.weighed[key] = tick
                    self.events.append({'tick': tick, 'object': key, 'target': 'pan', 'kind': 'weighed'})
                elif key in self.weighed and tick > self.weighed[key] and self.predicate(i, 'pad_'+key, row):
                    self.completed[key] = tick
                    self.events.append({'tick': tick, 'object': key, 'target': 'pad_'+key, 'kind': 'completed_object'})
        return self.final_ok

    @property
    def phase(self):
        return len(self.completed)

    @property
    def final_ok(self):
        return len(self.completed) == len(self.keys)
