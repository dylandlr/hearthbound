"""Finite-stock task allocation reference. SYNTHETIC ONLY; no Minecraft adapter.

At tick t every idle actor selects from its published snapshot. All choices are
validated before effects, then a precomputed policy-independent priority resolves
extractions. One step advances to t+1, completes due tasks, assembles products,
and refreshes direct sight for idle actors physically at a source. Busy tasks
advance through empty-action steps. The fixed horizon includes all elapsed ticks.
Public hub buffers, cargo-in-transit counts, and inspection intentions are supplied
game information; this environment cannot establish learned communication benefit.
"""
from dataclasses import dataclass, field
import math
import random


SCHEMA = "hearthbound.colony-task-observation.v0.4"
HUB_SCALE = 8.0  # Two sites per type, each initially holding at most four items.
ACTIONS = ("WAIT",) + tuple(f"INSPECT_SITE_{i}" for i in range(1, 5)) + tuple(
    f"HAUL_SITE_{i}" for i in range(1, 5))
FEATURES = ("time_remaining", "hub_a", "hub_b", "pending_a", "pending_b", "at_hub") + tuple(
    f"site_{i}_{name}" for i in range(1, 5) for name in
    ("type_a", "type_b", "travel", "known", "quantity", "age", "at_site", "other_inspections"))
assert len(FEATURES) == 38 and len(ACTIONS) == 9


def mask(observation):
    """Only published features control admission; hidden stock is never consulted."""
    if len(observation) != len(FEATURES) or any(
            not math.isfinite(v) or not 0 <= v <= 1 for v in observation):
        raise ValueError("Invalid observation vector")
    for site in range(4):
        offset = 6 + 8 * site
        if observation[offset] + observation[offset + 1] != 1:
            raise ValueError("Invalid public source type")
    # Busy actors have no at-position flag. ready() remains the execution gate.
    has_position = observation[5] == 1 or any(observation[12 + 8 * i] == 1 for i in range(4))
    active = observation[0] > 0 and has_position
    inspect = (active,) * 4
    haul = tuple(active and observation[12 + 8 * i] == 1
                 and observation[9 + 8 * i] == 1
                 and observation[10 + 8 * i] > 0
                 and observation[11 + 8 * i] == 0 for i in range(4))
    return (True,) + inspect + haul


@dataclass
class _Site:
    position: int
    kind: int
    stock: int


@dataclass
class _Agent:
    position: int = 0
    task: str | None = None
    site: int | None = None
    finish_tick: int = 0
    cargo: int | None = None
    travel_remaining: int = 0
    knowledge: list = field(default_factory=lambda: [None] * 4)


class Env:
    """Two-ingredient production with learned choices outside this class.

    Source coordinates/types are supplied map knowledge. Source stock is private
    until directly sensed. Public intent is only an announcement, not a reserved
    resource. The evaluator-only event ledger and metrics must not enter actors.
    """
    def __init__(self, seed, agents=2, horizon=64, regime="standard"):
        if type(seed) is not int or type(agents) is not int or agents < 1:
            raise ValueError("Invalid seed or agent count")
        if type(horizon) is not int or horizon < 1:
            raise ValueError("Invalid horizon")
        if regime not in ("standard", "long_routes", "scarce_b"):
            raise ValueError("Unknown regime")
        self.agents, self.horizon, self.regime = agents, horizon, regime
        self.tick, self.done, self.events = 0, False, []
        locations = list(range(-12, -6)) + list(range(7, 13)) if regime == "long_routes" else (
            list(range(-6, 0)) + list(range(1, 7)))
        positions = random.Random(f"layout:{seed}").sample(locations, 4)
        kinds = [0, 0, 1, 1]
        random.Random(f"types:{seed}").shuffle(kinds)
        stock_rng = random.Random(f"stock:{seed}")
        quantities = [stock_rng.randint(1, 4) for _ in range(4)]
        self._sites = [_Site(pos, kind, 1 if regime == "scarce_b" and kind == 1 else quantity)
                       for pos, kind, quantity in zip(positions, kinds, quantities)]
        self._agents = [_Agent() for _ in range(agents)]
        priority_rng = random.Random(f"priority:{seed}")
        self._priorities = [tuple(priority_rng.sample(range(agents), agents)) for _ in range(horizon)]
        self._hub = [0, 0]
        self._initial = [sum(s.stock for s in self._sites if s.kind == kind) for kind in (0, 1)]
        self._produced = self._denials = self._inspections = self._travel = 0
        self._delivered = [0, 0]

    def _agent(self, agent):
        if type(agent) is not int or not 0 <= agent < self.agents:
            raise ValueError("Unknown agent")
        return self._agents[agent]

    def ready(self):
        return [] if self.done else [i for i, a in enumerate(self._agents) if a.task is None]

    def obs(self, agent):
        actor = self._agent(agent)
        pending = [sum(a.cargo == kind for a in self._agents) for kind in (0, 1)]
        values = [max(0, self.horizon - self.tick) / self.horizon,
                  self._hub[0] / HUB_SCALE, self._hub[1] / HUB_SCALE,
                  pending[0] / self.agents, pending[1] / self.agents,
                  float(actor.task is None and actor.position == 0)]
        for index, source in enumerate(self._sites):
            knowledge = actor.knowledge[index]
            known = knowledge is not None
            quantity, observed = knowledge if known else (0, self.tick - self.horizon)
            intents = sum(i != agent and other.task == "INSPECT" and other.site == index
                          for i, other in enumerate(self._agents))
            values.extend((float(source.kind == 0), float(source.kind == 1),
                           min(1., abs(actor.position - source.position) / 24),
                           float(known), quantity / 4, min(1., (self.tick - observed) / self.horizon),
                           float(actor.task is None and actor.position == source.position),
                           intents / max(1, self.agents - 1)))
        return tuple(values)

    def _refresh_local(self):
        for i, actor in enumerate(self._agents):
            if actor.task is not None:
                continue
            for index, source in enumerate(self._sites):
                if actor.position == source.position:
                    actor.knowledge[index] = (source.stock, self.tick)
                    self.events.append(dict(tick=self.tick, event="DIRECT_OBSERVATION",
                                            agent=i, site=index, quantity=source.stock))

    def step(self, actions):
        if self.done:
            raise ValueError("Episode already finished")
        if not isinstance(actions, dict) or any(type(k) is not int for k in actions):
            raise ValueError("Actions must map integer agent IDs to action indices")
        idle = self.ready()
        if set(actions) != set(idle):
            raise ValueError("Supply exactly the idle agents' simultaneous actions")
        # Validate every snapshot before any action mutates hidden state.
        for i in idle:
            choice = actions[i]
            if type(choice) is not int or not 0 <= choice < len(ACTIONS) or not mask(self.obs(i))[choice]:
                raise ValueError("Action outside the published capability mask")
        personal = [-0.002] * self.agents
        for i in self._priorities[self.tick]:
            if i not in actions:
                continue
            actor, choice = self._agents[i], actions[i]
            if choice == 0:
                actor.task, actor.finish_tick = "WAIT", self.tick + 1
                continue
            index = choice - 1 if choice <= 4 else choice - 5
            source = self._sites[index]
            actor.site = index
            if choice <= 4:
                distance = abs(actor.position - source.position)
                actor.task, actor.finish_tick = "INSPECT", self.tick + max(1, distance)
                actor.travel_remaining = distance
                self.events.append(dict(tick=self.tick, event="INSPECT_STARTED", agent=i, site=index))
            elif source.stock <= 0:
                self._denials += 1
                personal[i] -= 0.05
                actor.task, actor.finish_tick = "DENIED", self.tick + 1
                self.events.append(dict(tick=self.tick, event="PICKUP_DENIED", agent=i, site=index))
            else:
                source.stock -= 1
                actor.knowledge[index] = (source.stock, self.tick)
                actor.cargo = source.kind
                actor.task, actor.finish_tick = "HAUL", self.tick + max(1, abs(actor.position))
                actor.travel_remaining = abs(actor.position)
                self.events.append(dict(tick=self.tick, event="EXTRACTED", agent=i,
                                        site=index, kind=source.kind, quantity=1))
        self.tick += 1
        for i, actor in enumerate(self._agents):
            if actor.travel_remaining > 0:
                actor.travel_remaining -= 1
                self._travel += 1
            if actor.task is None or actor.finish_tick > self.tick:
                continue
            if actor.task == "INSPECT":
                actor.position = self._sites[actor.site].position
                self._inspections += 1
            elif actor.task == "HAUL":
                kind = actor.cargo
                self._hub[kind] += 1
                self._delivered[kind] += 1
                actor.position, actor.cargo = 0, None
                self.events.append(dict(tick=self.tick, event="DELIVERED", agent=i,
                                        kind=kind, quantity=1))
            actor.task, actor.site = None, None
        products = min(self._hub)
        self._hub[0] -= products
        self._hub[1] -= products
        self._produced += products
        if products:
            self.events.append(dict(tick=self.tick, event="PRODUCED", quantity=products))
        self._refresh_local()
        self.done = self.tick >= self.horizon
        return float(products), personal, self.done

    def metrics(self):
        source = [sum(s.stock for s in self._sites if s.kind == kind) for kind in (0, 1)]
        transit = [sum(a.cargo == kind for a in self._agents) for kind in (0, 1)]
        residual = [self._initial[k] - source[k] - self._hub[k] - transit[k] - self._produced
                    for k in (0, 1)]
        return dict(produced=self._produced, deliveredA=self._delivered[0],
                    deliveredB=self._delivered[1], denials=self._denials,
                    totalinspections=self._inspections, totaltravel=self._travel,
                    source_items=sum(source), hub_items=sum(self._hub), transit_items=sum(transit),
                    initial_items=sum(self._initial), conservation_residual=sum(residual),
                    conservation_residual_A=residual[0], conservation_residual_B=residual[1],
                    initial_A=self._initial[0], initial_B=self._initial[1],
                    source_A=source[0], source_B=source[1], hub_A=self._hub[0], hub_B=self._hub[1],
                    transit_A=transit[0], transit_B=transit[1],
                    attainable_material_bound=min(self._initial), tick=self.tick,
                    horizon=self.horizon, minecraft_worlds=0)


def scripted_nearest(observation):
    available = mask(observation)
    for site in range(4):
        if available[5 + site]:
            return 5 + site
    candidates = [i for i in range(4) if available[1 + i]
                  and (observation[9 + 8 * i] == 0 or observation[10 + 8 * i] > 0)]
    return 1 + min(candidates, key=lambda i: (observation[8 + 8 * i], i)) if candidates else 0


def scripted_balance(observation, agents=2):
    """Equal-information heuristic; actor count is declared public scenario configuration."""
    if type(agents) is not int or agents < 1:
        raise ValueError("Invalid public agent count")
    available = mask(observation)
    balances = (observation[1] * HUB_SCALE + observation[3] * agents,
                observation[2] * HUB_SCALE + observation[4] * agents)
    candidates = []
    for site in range(4):
        offset = 6 + 8 * site
        if not available[1 + site] or (observation[offset + 3] == 1
                                     and observation[offset + 4] == 0):
            continue
        kind = 0 if observation[offset] == 1 else 1
        surplus = balances[kind] > balances[1 - kind] + 1e-9
        effort = observation[offset + 2] + .35 * observation[offset + 7]
        uncertainty = .1 * (1 - observation[offset + 3])
        candidates.append((surplus, effort + uncertainty, site))
    if not candidates:
        return 0
    site = min(candidates)[2]
    return 5 + site if available[5 + site] else 1 + site
