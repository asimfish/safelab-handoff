import math
KEYS="ABCDE"
class PlaceTen:

    def __init__(self, profile, order, origin):
        self.profile = profile
        self.order = order
        self.origin = origin
        self.phase = 0
        self.failure = None
        self.events = []
        self.lifted = False
        self.count = 0
        self.last_tick = None
        self.final_ok = False
        self._initial_z = None
        self._phase_min_z = None
        self._guard_contact_seen = False
        self.guard_triggered_phases = set()
        scene = profile['scene']
        self.floor = scene['table_top'] - 0.1
        self.h = scene['half_height']
        self.supports = scene['supports']
        self.bottom = [scene.get('object_bottom_offsets', {}).get(k, self.h) for k in KEYS]
        self.sequence = [(KEYS.index(KEYS[int(o) - 1]), target) for o in order for target in ('pan', 'pad_' + KEYS[int(o) - 1])]

    def predicate(self, ix, target, poses, contacts, attached, ups):
        p = poses[ix]
        c = self.supports[target]
        b = self.bottom[ix]
        ox, oy, oz = self.origin
        if (p[0] - ox - c[0]) ** 2 + (p[1] - oy - c[1]) ** 2 > 0.025 ** 2 or ups[ix] < 0.97 or KEYS[ix] in attached:
            return False
        obj = [e for e in contacts if e['object'] == KEYS[ix] and e['contact_count'] > 0]
        if any(('/Robot/' in e['actor'] for e in obj)):
            return False
        token = '/Balance/' if target == 'pan' else '/' + target
        support = any((token in e['actor'] for e in obj))
        return support or abs(p[2] - oz - c[2] - b) <= 0.005

    def observe(self, row):
        tick = row['tick']
        poses = row['poses']
        contacts = row['contacts']
        attached = row.get('attached_keys', [])
        if self.last_tick is not None and tick != self.last_tick + 1:
            raise ValueError('missing_native_tick')
        self.last_tick = tick
        if self._initial_z is None:
            self._initial_z = [p[2] - self.origin[2] for p in poses]
        if len(poses) != 5 or any((len(p) != 7 or not all((math.isfinite(x) for x in p)) for p in poses)):
            raise ValueError('invalid_pose')
        ups = [1 - 2 * (p[4] * p[4] + p[5] * p[5]) / sum((q * q for q in p[3:])) for p in poses]
        if any((p[2] - self.origin[2] < self.floor for p in poses)):
            self.failure = 'object_fell'
        if any((z < 0.5 for z in ups)):
            self.failure = 'object_toppled'
        if self.phase < 10 and self.failure is None:
            ix, target = self.sequence[self.phase]
            source = 'pad_' + KEYS[ix] if target == 'pan' else 'pan'
            source_z = self.supports[source][2] + self.bottom[ix]
            lift = 0.025 if source == 'pan' else self.profile['motion']['lift_height']
            z = poses[ix][2] - self.origin[2]
            self._phase_min_z = z if self._phase_min_z is None else min(self._phase_min_z, z)
            if self._initial_z[ix] >= source_z + 0.65 * lift:
                self.guard_triggered_phases.add(self.phase)
                self._guard_contact_seen = self._guard_contact_seen or any((e['object'] == KEYS[ix] and e['contact_count'] > 0 and ('/Robot/' in e['actor']) for e in contacts))
                anchor = max(source_z, self._phase_min_z)
                if self._guard_contact_seen and z - anchor >= 0.65 * lift:
                    self.lifted = True
            elif z - source_z >= 0.65 * lift:
                self.lifted = True
            self.count = self.count + 1 if self.lifted and self.predicate(ix, target, poses, contacts, attached, ups) else 0
            if self.count >= 30:
                self.events.append({'phase': self.phase + 1, 'tick': tick, 'object': KEYS[ix], 'target': target, 'placement_ticks': 30})
                self.phase += 1
                self.count = 0
                self.lifted = False
                self._phase_min_z = None
                self._guard_contact_seen = False
        self.final_ok = self.phase == 10 and self.failure is None and all((self.predicate(i, 'pad_' + k, poses, contacts, attached, ups) for i, k in enumerate(KEYS)))
        return self.final_ok
