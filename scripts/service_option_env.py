#!/usr/bin/env python3
"""Bounded surrogate of the opt-in Minecraft service menu. SYNTHETIC receipts.

Only private local observations/received requests enter menus. Public geometry is
known. Executor arbitration can refuse a selected job, never reveal candidates.
Time is in seconds (20 Minecraft ticks); native pathfinding/Create are NOT simulated.
"""
from dataclasses import dataclass, field
import math
import numpy as np

SCHEMA = 'hearthbound.private-service-menu.v0.22'
FEATURES = ('bias', 'need_units', 'distance', 'evidence_age', 'competition',
            'partner_success', 'supply', 'observe', 'carry_request', 'wait')
KINDS = ('SUPPLY_WHEAT', 'OBSERVE_BUFFER', 'CARRY_REQUEST', 'WAIT')
GAMMA = .98
PERSONAL_WEIGHT = .75


def features(kind, units=0, distance=0., age_ticks=0, partner_success=.5):
    return (1., min(1., units / 64), min(1., distance / 64), min(1., age_ticks / 600),
            0., partner_success, *(float(kind == k) for k in KINDS))


def encode(menu):
    """Own candidate + own-menu mean + own-menu max; no privileged input."""
    x = np.asarray([c['features'] for c in menu], dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 10 or not 1 <= len(x) <= 73 or not np.isfinite(x).all():
        raise ValueError('Invalid private menu')
    if np.any((x < 0) | (x > 1)) or np.any(x[:, 0] != 1) or np.any(x[:, 6:].sum(axis=1) != 1):
        raise ValueError('Invalid private feature contract')
    return np.concatenate((x, np.broadcast_to(x.mean(axis=0), x.shape),
                           np.broadcast_to(x.max(axis=0), x.shape)), axis=1)


def authored(menu):
    priors = dict(zip(KINDS, (3., .6, 1., 0.)))
    return max(range(len(menu)), key=lambda i: (priors[menu[i]['kind']] - .3 * menu[i]['features'][2],
                                               -i))


@dataclass
class Actor:
    pos: np.ndarray
    needs: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    partners: dict = field(default_factory=dict)
    sent: set = field(default_factory=set)
    active: dict | None = None
    until: int = 0


class Env:
    def __init__(self, seed, horizon=120):
        self.seed, self.horizon, self.t = seed, horizon, 0
        rng = np.random.default_rng(seed)
        length, gap = int(rng.integers(26, 39)), int(rng.integers(12, 21))
        self.sources = np.asarray(((length, 3.), (length, 3. + gap)))
        self.outputs = np.asarray(((4., 3.), (4., 3. + gap)))
        self.mills = self.outputs + (7., 0.)
        self.actors = [Actor(p + rng.uniform(-1, 1, 2)) for p in
                       (self.outputs[0], self.sources[0], self.outputs[1], self.sources[1])]
        self.stock = [0, 0]; self.wheat = [16, 16]; self.target = [2, 1]
        self.schedule = ((0, (2, 1)), (40, (2, 4)), (80, (5, 4)))
        self.revisions = [0, 0]; self.latest = [None, None]
        self.machine_owner = {}; self.source_owner = {}
        self.events = []; self.produced = [0] * 4; self.costs = [0.] * 4
        self.sent_count = 0; self.received = 0; self.failures = 0
        self.sense()

    def sense(self):
        for a, actor in enumerate(self.actors):
            if actor.active and actor.active['kind'] == 'SUPPLY_WHEAT':
                continue  # native motor owns sensing, as in the live adapter
            for s, pos in enumerate(self.sources):
                if np.linalg.norm(actor.pos - pos) <= 8:
                    actor.sources[s] = (self.wheat[s], self.t)
            for s, pos in enumerate(self.outputs):
                if np.linalg.norm(actor.pos - pos) > 8 or self.target[s] == 0:
                    continue
                units = max(0, self.target[s] - self.stock[s]); prior = actor.needs.get(s)
                if prior and prior['sender'] is None and prior['units'] == units and self.t - prior['tick'] < 5:
                    continue
                self.revisions[s] += 1
                need = dict(units=units, tick=self.t, revision=self.revisions[s], sender=None)
                actor.needs[s] = need; self.latest[s] = need.copy()

    def menu(self, a):
        actor = self.actors[a]; menu = []
        fresh = [s for s, (units, tick) in actor.sources.items() if units > 0 and self.t - tick <= 2]
        known = {s: k for s, k in actor.needs.items() if self.t - k['tick'] <= 30}
        def add(kind, s=None, source=None, need=None, distance=0.):
            partner = None if need is None else need['sender']
            success, count = actor.partners.get(partner, (0, 0)) if partner is not None else (0, 0)
            f = features(kind, 0 if need is None else need['units'], distance,
                         0 if need is None else (self.t - need['tick']) * 20, (success + 1) / (count + 2))
            menu.append(dict(id=f'{kind}:{s}:{source}', kind=kind, site=s, source=source,
                             features=f, need=None if need is None else need.copy()))
        for s, need in sorted(known.items()):
            if need['units'] <= 0 or self.target[s] == 0:
                continue
            for source in sorted(fresh):
                blocks = (np.linalg.norm(actor.pos - self.sources[source]) +
                          np.linalg.norm(self.sources[source] - self.mills[s]) +
                          np.linalg.norm(self.mills[s] - self.outputs[s]))
                add('SUPPLY_WHEAT', s, source, need, blocks)
            if not fresh:
                source = min(range(2), key=lambda i: np.linalg.norm(actor.pos - self.sources[i]))
                add('CARRY_REQUEST', s, source, need, np.linalg.norm(actor.pos - self.sources[source]))
        for s, pos in enumerate(self.outputs):
            if self.target[s] > 0 and s not in known:
                add('OBSERVE_BUFFER', s, distance=np.linalg.norm(actor.pos - pos))
        add('WAIT')
        # Stable identity tie-break like Java. No identity is a network feature.
        return sorted(menu, key=lambda c: c['id'])

    def ready(self):
        return [i for i, a in enumerate(self.actors) if a.active is None and self.t >= a.until]

    def start(self, a, candidate):
        if a not in self.ready():
            raise ValueError('Actor already owns an option')
        legal = {c['id']: c for c in self.menu(a)}
        if candidate['id'] not in legal or legal[candidate['id']]['features'] != candidate['features']:
            raise ValueError('Foreign or stale private menu')
        option = dict(candidate, start=self.t, phase='MOVE', cargo=0, moved=0., sent=0)
        actor = self.actors[a]; actor.active = option
        if option['kind'] == 'SUPPLY_WHEAT':
            s, source = option['site'], option['source']
            if s in self.machine_owner or source in self.source_owner or self.wheat[source] <= 0 or self.stock[s] >= self.target[s]:
                option['phase'] = 'REFUSED'
            else:
                self.machine_owner[s] = a; self.source_owner[source] = a
                option['phase'] = 'TO_SOURCE'

    def _move(self, actor, goal):
        delta = goal - actor.pos; distance = float(np.linalg.norm(delta))
        moved = min(3., max(0., distance - 2.))
        if moved: actor.pos += delta * (moved / distance)
        actor.active['moved'] += moved
        return distance - moved <= 2.0000001, moved

    def step(self):
        personal = np.zeros(4); completed = []; total_output = 0
        self.t += 1
        for tick, target in self.schedule:
            if self.t == tick: self.target = list(target)
        self.sense()
        for a, actor in enumerate(self.actors):
            o = actor.active
            if o is None: continue
            kind, s = o['kind'], o['site']; done, success, output, moved, sends = False, False, 0, 0., 0
            if kind == 'WAIT':
                done = self.t - o['start'] >= 2; success = done
            elif kind == 'OBSERVE_BUFFER':
                k = actor.needs.get(s)
                if k and k['sender'] is None and k['tick'] >= o['start']:
                    done = success = True
                else: _, moved = self._move(actor, self.outputs[s])
            elif kind == 'CARRY_REQUEST':
                k = actor.needs.get(s)
                if k is None or self.t - k['tick'] > 30 or k['units'] == 0:
                    done = True
                elif any(n > 0 and self.t - t <= 2 for n, t in actor.sources.values()):
                    done = success = True
                else:
                    for b, peer in enumerate(self.actors):
                        token = (b, s, k['revision'])
                        if b == a or np.linalg.norm(actor.pos - peer.pos) > 12 or token in actor.sent: continue
                        actor.sent.add(token); sends += 1; self.sent_count += 1
                        old = peer.needs.get(s)
                        if old is None or k['revision'] > old['revision']:
                            peer.needs[s] = dict(k, sender=a); self.received += 1
                            done = success = True
                    if not done: _, moved = self._move(actor, self.sources[o['source']])
            elif o['phase'] == 'REFUSED':
                done = True; self.failures += 1
            elif o['phase'] == 'TO_SOURCE':
                reached, moved = self._move(actor, self.sources[o['source']])
                if reached:
                    self.wheat[o['source']] -= 1; o['cargo'] = 1; o['phase'] = 'TO_MILL'
            elif o['phase'] == 'TO_MILL':
                reached, moved = self._move(actor, self.mills[s])
                if reached: o['phase'] = 'PROCESS'; o['process_until'] = self.t + 3
            elif o['phase'] == 'PROCESS':
                if self.t >= o['process_until']: o['phase'] = 'TO_OUTPUT'
            elif o['phase'] == 'TO_OUTPUT':
                reached, moved = self._move(actor, self.outputs[s])
                if reached:
                    self.stock[s] += 1; o['cargo'] = 0; output = 1; done = success = True
                    del self.machine_owner[s]; del self.source_owner[o['source']]
                    self.events.append(dict(origin='SYNTHETIC', type='OUTPUT_DELIVERED', tick=self.t,
                                            actor=a, site=s, source=o['source'], units=1))
            if self.t - o['start'] >= 30 and kind in ('CARRY_REQUEST', 'OBSERVE_BUFFER'):
                done = True
            # Time, travel and message costs are separate from output. No message bonus.
            cost = .002 + .01 * moved + .02 * sends
            self.costs[a] += cost; personal[a] = output - cost
            self.produced[a] += output; total_output += output
            if done:
                partner = None if o['need'] is None else o['need']['sender']
                if partner is not None:
                    wins, count = actor.partners.get(partner, (0, 0)); actor.partners[partner] = (wins + int(success), count + 1)
                actor.active = None; actor.until = self.t  # all recovery time is explicit next WAIT, if chosen
                completed.append(a)
        return personal, float(total_output), completed

    def result(self):
        cargo = sum(a.active['cargo'] for a in self.actors if a.active)
        if sum(self.wheat) + sum(self.stock) + cargo != 32:
            raise AssertionError('Synthetic material conservation failed')
        return dict(seed=self.seed, origin='SYNTHETIC', output=sum(self.stock), per_site=self.stock.copy(),
                    per_actor=self.produced.copy(), costs=self.costs.copy(), sent=self.sent_count,
                    received=self.received, executor_refusals=self.failures, unfinished=sum(a.active is not None for a in self.actors),
                    schedule=list(self.schedule), material_conserved=True)


def episode(world, policy, transition=None, on_tick=None):
    pending = {}
    def finish(a, terminal):
        t = pending.pop(a); t['next'] = encode(world.menu(a)); t['terminal'] = terminal
        if t['duration'] < 1: raise AssertionError('Zero-duration transition')
        if transition: transition(t)
    while world.t < world.horizon:
        for a in world.ready():
            if a in pending: finish(a, False)
            menu = world.menu(a); encoded = encode(menu); choice = policy(menu, encoded)
            pending[a] = dict(x=encoded[choice].copy(), reward=0., personal=0., colony=0., duration=0)
            world.start(a, menu[choice])
        personal, colony, completed = world.step()
        for a, item in pending.items():
            discount = GAMMA ** item['duration']
            item['personal'] += discount * personal[a]; item['colony'] += discount * colony
            item['reward'] += discount * (PERSONAL_WEIGHT * personal[a] + (1 - PERSONAL_WEIGHT) * colony)
            item['duration'] += 1
        if on_tick: on_tick()
    for a in list(pending): finish(a, True)
    return world.result()
