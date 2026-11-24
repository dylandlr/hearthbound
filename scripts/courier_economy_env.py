"""Optional finite-stock physical-message research environment; NOT Minecraft.

No profession, recipient assignment, free global task board, or delivery reward
exists. SHARE emits one report selected by an engineered round-robin scheduler;
choosing the payload/language is outside this pilot. GO actions follow known
one-dimensional roads and take physical simulation ticks. Policy observations
contain only local sight, private memory and permitted reports. Evaluator events
and metrics are privileged and must never be policy inputs.
"""
from dataclasses import dataclass, field
import math
import random
import re

SCHEMA = "hearthbound.physical-message-economy.v0.1"
ACTIONS = ("WAIT", "GO_HUB") + tuple(f"GO_SITE_{i}" for i in range(1, 5)) + ("PICKUP", "DROP", "SHARE")
FEATURES = ("time_remaining", "idle", "cargo_a", "cargo_b", "travel_cost",
            "local_peers", "shareable", "at_hub", "hub_travel", "hub_known",
            "hub_a", "hub_b", "hub_age", "hub_report") + tuple(
    f"site_{i}_{name}" for i in range(1, 5) for name in
    ("type_a", "type_b", "travel", "at", "known", "quantity", "age", "report"))
F = {name: i for i, name in enumerate(FEATURES)}
PROTOCOLS = ("local", "no_messages", "unread", "instant", "no_relay")
TTL = 24
MAX_HOPS = 8
STOCK_SCALE = 24.0
COORDINATES = (0, -4, -2, 2, 4)


def mask(observation):
    """Admission depends only on published features; empty-source races can fail."""
    if len(observation) != len(FEATURES) or any(
            not math.isfinite(x) or x < 0 or x > 1 for x in observation):
        raise ValueError("Invalid physical-message observation")
    active = observation[F["time_remaining"]] > 0 and observation[F["idle"]] == 1
    at_hub = observation[F["at_hub"]] == 1
    at_sites = [observation[F[f"site_{i}_at"]] == 1 for i in range(1, 5)]
    cargo = observation[F["cargo_a"]] + observation[F["cargo_b"]] > 0
    return (True, active and not at_hub) + tuple(active and not at for at in at_sites) + (
        active and any(at_sites) and not cargo,
        active and at_hub and cargo,
        active and observation[F["shareable"]] > 0 and observation[F["local_peers"]] > 0)


@dataclass(frozen=True)
class Evidence:
    observation_id: str
    node: int
    quantities: tuple
    observed_tick: int
    observer: int


@dataclass(frozen=True)
class Knowledge:
    evidence: Evidence
    origin: str
    sender: int | None = None
    route: tuple = ()
    message_id: str | None = None


@dataclass
class _Agent:
    node: int = 0
    target: int | None = None
    remaining: int = 0
    cargo: int | None = None
    travel_cost: float = .75
    direct: dict = field(default_factory=dict)
    reports: dict = field(default_factory=dict)
    shared: dict = field(default_factory=dict)
    last_shared: dict = field(default_factory=dict)


class Env:
    """One hub, four finite resource sites, interchangeable capacity-one citizens.

    Each hub product consumes one A and one B. Stocks vary by world; node
    coordinates and resource types are supplied map knowledge. Reports preserve
    their original direct witness and clock through every physical handoff.
    'instant' is a declared free perfect-information comparison, not a local
    communication model. Frozen policies evaluated under it may fail to exploit
    the information; it is not an empirical upper bound on their performance.
    Each independent trial must supply a unique run_id. The deterministic
    manual default is for isolated inspection, not combined experimental logs.
    Provenance scope never enters physics RNGs or actor observation vectors.
    """
    def __init__(self, seed, agents=4, horizon=96, communication="local", trace=False, run_id=None):
        if type(seed) is not int or type(agents) is not int or not 1 <= agents <= 100:
            raise ValueError("Invalid seed/agent count")
        if type(horizon) is not int or not 1 <= horizon <= 10000:
            raise ValueError("Invalid horizon")
        if communication not in PROTOCOLS:
            raise ValueError("Unknown communication protocol")
        if run_id is None:
            run_id = f"manual:{communication}"
        if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,256}", run_id):
            raise ValueError("run_id must be a nonempty bounded ASCII trial identifier")
        self.seed, self.agents, self.horizon = seed, agents, horizon
        self.communication, self.trace = communication, bool(trace)
        self.tick, self.done, self.events = 0, False, []
        self.world_id = f"synthetic-courier-{seed}"
        self.run_id = run_id
        self._scope = f"{self.world_id}:run:{run_id}"
        kinds = [0, 0, 1, 1]
        random.Random(f"courier-types:{seed}").shuffle(kinds)
        self._kinds = kinds
        rng = random.Random(f"courier-stock:{seed}")
        self._stock = [rng.randint(0, 6) for _ in range(4)]
        self._hub = [0, 0]
        self._initial = [sum(q for q, k in zip(self._stock, kinds) if k == kind) for kind in (0, 1)]
        traits = random.Random(f"courier-traits:{seed}")
        self._agents = [_Agent(travel_cost=traits.uniform(.5, 1.)) for _ in range(agents)]
        priority = random.Random(f"courier-priority:{seed}")
        self._priorities = [tuple(priority.sample(range(agents), agents)) for _ in range(horizon)]
        self._counters = dict(produced=0, attempts=0, delivered=0, forwarded=0,
                              cross_site_deliveries=0, read_report_inputs=0,
                              report_present_for_travel=0, blocked=0, duplicates=0,
                              stale=0, expired=0, loop_rejected=0, empty_sends=0,
                              pickups=0, drops=0, pickup_denials=0, travel_ticks=0,
                              decision_count=0, direct_observations=0)
        self._per_agent = [dict(shares=0, deliveries=0, forwarded=0, cross_site_deliveries=0,
                                received=0, read_report_inputs=0, report_present_for_travel=0,
                                pickups=0, drops=0, travel_ticks=0, decisions=0,
                                personal_reward=0.) for _ in range(agents)]
        self._refresh_local()

    def _emit(self, event, **fields):
        if self.trace:
            self.events.append(dict(world_id=self.world_id, run_id=self.run_id,
                                    tick=self.tick, event=event, **fields))

    def _agent(self, agent):
        if type(agent) is not int or not 0 <= agent < self.agents:
            raise ValueError("Unknown agent")
        return self._agents[agent]

    def ready(self):
        return [] if self.done else [i for i, a in enumerate(self._agents) if a.remaining == 0]

    def _fresh(self, entry):
        return entry is not None and 0 <= self.tick - entry.evidence.observed_tick <= TTL

    def _quantities(self, node):
        if node == 0:
            return tuple(self._hub)
        return (self._stock[node - 1],)

    def _knowledge(self, agent, node):
        actor = self._agent(agent)
        direct = actor.direct.get(node)
        direct = direct if self._fresh(direct) else None
        if self.communication == "instant":
            # Explicit public-oracle condition; this is never labeled DIRECT.
            return Knowledge(Evidence(f"{self._scope}:public:{node}:{self.tick}", node,
                                      self._quantities(node), self.tick, -1), "PUBLIC")
        report = actor.reports.get(node) if self.communication != "unread" else None
        report = report if self._fresh(report) else None
        if direct is None:
            return report
        if report is None or direct.evidence.observed_tick >= report.evidence.observed_tick:
            return direct
        return report

    def _share_payload(self, agent):
        actor = self._agent(agent)
        eligible = []
        for node in range(5):
            if self.communication in ("no_relay", "instant"):
                entry = actor.direct.get(node)
            elif self.communication == "unread":
                # The identical fixed transport scheduler may carry sealed
                # reports. Actor features expose availability, never content.
                direct = actor.direct.get(node)
                report = actor.reports.get(node)
                direct = direct if self._fresh(direct) else None
                report = report if self._fresh(report) else None
                entry = direct if direct and (report is None or
                    direct.evidence.observed_tick >= report.evidence.observed_tick) else report
            else:
                entry = self._knowledge(agent, node)
            if (not self._fresh(entry) or len(entry.route) >= MAX_HOPS
                    or actor.shared.get(node) == entry.evidence.observation_id):
                continue
            eligible.append((actor.last_shared.get(node, -1), node, entry))
        # No inspection of recipients' private needs, inboxes or decisions.
        return min(eligible, key=lambda x: (x[0], x[1]))[2] if eligible else None

    def _peers(self, agent):
        actor = self._agent(agent)
        return [i for i, other in enumerate(self._agents)
                if i != agent and actor.remaining == other.remaining == 0 and actor.node == other.node]

    def obs(self, agent):
        actor = self._agent(agent)
        idle = actor.remaining == 0
        hub = self._knowledge(agent, 0)
        values = [max(0, self.horizon - self.tick) / self.horizon, float(idle),
                  float(actor.cargo == 0), float(actor.cargo == 1), actor.travel_cost,
                  len(self._peers(agent)) / max(1, self.agents - 1),
                  float(self._share_payload(agent) is not None), float(idle and actor.node == 0),
                  abs(COORDINATES[actor.node]) / 8., float(hub is not None),
                  hub.evidence.quantities[0] / STOCK_SCALE if hub else 0.,
                  hub.evidence.quantities[1] / STOCK_SCALE if hub else 0.,
                  (self.tick - hub.evidence.observed_tick) / TTL if hub else 1.,
                  float(hub is not None and hub.origin == "REPORT")]
        for node in range(1, 5):
            entry = self._knowledge(agent, node)
            values.extend((float(self._kinds[node - 1] == 0), float(self._kinds[node - 1] == 1),
                           abs(COORDINATES[actor.node] - COORDINATES[node]) / 8.,
                           float(idle and actor.node == node), float(entry is not None),
                           entry.evidence.quantities[0] / 6. if entry else 0.,
                           (self.tick - entry.evidence.observed_tick) / TTL if entry else 1.,
                           float(entry is not None and entry.origin == "REPORT")))
        return tuple(values)

    def _refresh_local(self):
        for i, actor in enumerate(self._agents):
            for memory in (actor.direct, actor.reports):
                for node, entry in list(memory.items()):
                    if not self._fresh(entry):
                        del memory[node]
                        self._counters["expired"] += 1
                        self._emit("MEMORY_EXPIRED", agent=i, observation_id=entry.evidence.observation_id)
            if actor.remaining:
                continue
            node = actor.node
            evidence = Evidence(f"{self._scope}:sight:{i}:{node}:{self.tick}", node,
                                self._quantities(node), self.tick, i)
            actor.direct[node] = Knowledge(evidence, "DIRECT", route=(i,))
            self._counters["direct_observations"] += 1
            self._emit("DIRECT_OBSERVATION", agent=i, node=node,
                       observation_id=evidence.observation_id, quantities=evidence.quantities)

    def _admit(self, recipient, sender, payload, message_id):
        """Transport reception does not grant direct observation or freshness."""
        actor = self._agent(recipient)
        evidence = payload.evidence
        if not self._fresh(payload):
            self._counters["stale"] += 1
            self._emit("REJECTED_STALE", recipient=recipient, message_id=message_id)
            return False
        if recipient in payload.route or len(payload.route) >= MAX_HOPS:
            self._counters["loop_rejected"] += 1
            self._emit("REJECTED_LOOP", recipient=recipient, message_id=message_id)
            return False
        previous = actor.reports.get(evidence.node)
        direct = actor.direct.get(evidence.node)
        if any(k is not None and k.evidence.observation_id == evidence.observation_id
               for k in (previous, direct)):
            self._counters["duplicates"] += 1
            self._emit("REJECTED_DUPLICATE", recipient=recipient, message_id=message_id)
            return False
        if ((previous and previous.evidence.observed_tick >= evidence.observed_tick)
                or (direct and direct.evidence.observed_tick >= evidence.observed_tick)):
            self._counters["stale"] += 1
            self._emit("REJECTED_SUPERSEDED", recipient=recipient, message_id=message_id)
            return False
        entry = Knowledge(evidence, "REPORT", sender, payload.route + (recipient,), message_id)
        actor.reports[evidence.node] = entry
        self._counters["delivered"] += 1
        self._per_agent[sender]["deliveries"] += 1
        self._per_agent[recipient]["received"] += 1
        forwarded = sender != evidence.observer
        cross_site = self._agents[sender].node != evidence.node
        self._counters["forwarded"] += int(forwarded)
        self._counters["cross_site_deliveries"] += int(cross_site)
        self._per_agent[sender]["forwarded"] += int(forwarded)
        self._per_agent[sender]["cross_site_deliveries"] += int(cross_site)
        self._emit("REPORT_DELIVERED", sender=sender, recipient=recipient, message_id=message_id,
                   observation_id=evidence.observation_id, original_observer=evidence.observer,
                   observed_tick=evidence.observed_tick, source_node=evidence.node,
                   quantities=evidence.quantities, parent_message_id=payload.message_id,
                   encounter_node=self._agents[sender].node, route=entry.route,
                   forwarded=forwarded, cross_site=cross_site)
        return True

    def step(self, actions):
        if self.done:
            raise ValueError("Episode already finished")
        if not isinstance(actions, dict) or any(type(k) is not int for k in actions):
            raise ValueError("Actions must map integer agent IDs to action indices")
        idle = self.ready()
        if set(actions) != set(idle):
            raise ValueError("Supply exactly the idle agents' simultaneous actions")
        snapshots = {i: self.obs(i) for i in idle}
        for i in idle:
            action = actions[i]
            if type(action) is not int or not 0 <= action < len(ACTIONS) or not mask(snapshots[i])[action]:
                raise ValueError("Action outside published local capability mask")
        # Capture ALL messages and encounter sets before any agent is changed.
        sends = [(i, self._share_payload(i), self._peers(i)) for i in idle if actions[i] == 8]
        personal = [-.002] * self.agents
        for i in idle:
            self._counters["decision_count"] += 1
            self._per_agent[i]["decisions"] += 1
            for node in range(5):
                entry = self._knowledge(i, node)
                if entry is None or entry.origin != "REPORT":
                    continue
                self._counters["read_report_inputs"] += 1
                self._per_agent[i]["read_report_inputs"] += 1
                self._emit("REPORT_POLICY_INPUT", agent=i, action=ACTIONS[actions[i]],
                           observation_id=entry.evidence.observation_id, message_id=entry.message_id)
                if actions[i] == node + 1:
                    self._counters["report_present_for_travel"] += 1
                    self._per_agent[i]["report_present_for_travel"] += 1
                    self._emit("TRAVEL_WITH_REPORT_INPUT", agent=i, node=node,
                               observation_id=entry.evidence.observation_id)
        for sender, payload, recipients in sends:
            self._per_agent[sender]["shares"] += 1
            self._counters["attempts"] += 1
            personal[sender] -= .01
            message_id = f"{self._scope}:send:{self.tick}:{sender}"
            if payload is None:
                self._counters["empty_sends"] += 1
                self._emit("SEND_EMPTY", sender=sender, message_id=message_id)
                continue
            actor = self._agents[sender]
            actor.shared[payload.evidence.node] = payload.evidence.observation_id
            actor.last_shared[payload.evidence.node] = self.tick
            self._emit("REPORT_SENT", sender=sender, message_id=message_id,
                       observation_id=payload.evidence.observation_id, recipients=recipients,
                       original_observer=payload.evidence.observer,
                       observed_tick=payload.evidence.observed_tick,
                       source_node=payload.evidence.node, quantities=payload.evidence.quantities,
                       route=payload.route, parent_message_id=payload.message_id)
            for recipient in recipients:
                if self.communication == "no_messages":
                    self._counters["blocked"] += 1
                    self._emit("TRANSPORT_BLOCKED", recipient=recipient, message_id=message_id)
                else:
                    self._admit(recipient, sender, payload, message_id)
        for i in self._priorities[self.tick]:
            if i not in actions:
                continue
            actor, action = self._agents[i], actions[i]
            if 1 <= action <= 5:
                target = action - 1
                actor.target = target
                actor.remaining = abs(COORDINATES[actor.node] - COORDINATES[target])
                self._emit("TRAVEL_STARTED", agent=i, source=actor.node, target=target,
                           duration=actor.remaining)
            elif action == 6:
                node = actor.node
                if self._stock[node - 1] == 0:
                    self._counters["pickup_denials"] += 1
                    personal[i] -= .01
                    self._emit("PICKUP_DENIED", agent=i, node=node)
                else:
                    self._stock[node - 1] -= 1
                    actor.cargo = self._kinds[node - 1]
                    self._counters["pickups"] += 1
                    self._per_agent[i]["pickups"] += 1
                    personal[i] -= .002
                    self._emit("PICKUP", agent=i, node=node, kind=actor.cargo)
            elif action == 7:
                self._hub[actor.cargo] += 1
                self._counters["drops"] += 1
                self._per_agent[i]["drops"] += 1
                personal[i] -= .002
                self._emit("DROP", agent=i, node=0, kind=actor.cargo)
                actor.cargo = None
        self.tick += 1
        for i, actor in enumerate(self._agents):
            if actor.remaining:
                actor.remaining -= 1
                personal[i] -= .004 * actor.travel_cost
                self._counters["travel_ticks"] += 1
                self._per_agent[i]["travel_ticks"] += 1
                if actor.remaining == 0:
                    actor.node, actor.target = actor.target, None
                    self._emit("TRAVEL_ARRIVED", agent=i, node=actor.node)
            self._per_agent[i]["personal_reward"] += personal[i]
        products = min(self._hub)
        if products:
            self._hub[0] -= products
            self._hub[1] -= products
            self._counters["produced"] += products
            self._emit("PRODUCT_VERIFIED", quantity=products, input_a=products, input_b=products)
        self._refresh_local()
        self.done = self.tick >= self.horizon
        return float(products), personal, self.done

    def metrics(self):
        source = [sum(q for q, k in zip(self._stock, self._kinds) if k == kind) for kind in (0, 1)]
        cargo = [sum(a.cargo == kind for a in self._agents) for kind in (0, 1)]
        produced = self._counters["produced"]
        residual = [self._initial[k] - source[k] - self._hub[k] - cargo[k] - produced for k in (0, 1)]
        return dict(self._counters, conservation_residual_A=residual[0],
                    conservation_residual_B=residual[1], conservation_residual=sum(residual),
                    initial_A=self._initial[0], initial_B=self._initial[1],
                    source_A=source[0], source_B=source[1], hub_A=self._hub[0], hub_B=self._hub[1],
                    cargo_A=cargo[0], cargo_B=cargo[1],
                    attainable_material_bound=min(self._initial), tick=self.tick,
                    horizon=self.horizon, minecraft_worlds=0,
                    per_agent=[dict(row) for row in self._per_agent])


def scripted_local(observation):
    """Observation-only productive heuristic, without a fixed courier assignment.

    It does not optimize information delivery; it is a deliberately transparent
    work baseline under the same information boundary as the learned actor.
    """
    available = mask(observation)
    if available[7]:
        return 7
    if observation[F["cargo_a"]] + observation[F["cargo_b"]] > 0:
        return 1 if available[1] else 0
    if available[6]:
        for node in range(1, 5):
            if observation[F[f"site_{node}_at"]] and observation[F[f"site_{node}_quantity"]] > 0:
                return 6
    candidates = []
    for node in range(1, 5):
        if not available[node + 1]:
            continue
        known = observation[F[f"site_{node}_known"]]
        quantity = observation[F[f"site_{node}_quantity"]]
        if known and quantity == 0:
            continue
        kind = 0 if observation[F[f"site_{node}_type_a"]] else 1
        hub_a, hub_b = observation[F["hub_a"]], observation[F["hub_b"]]
        surplus = hub_a > hub_b if kind == 0 else hub_b > hub_a
        candidates.append((surplus, observation[F[f"site_{node}_travel"]], node))
    return min(candidates)[2] + 1 if candidates else 0
