"""Recurring local demand and physical reports. SYNTHETIC, not Forge behavior.

Three supplied-map locations, one-item cargo, finite material and two-tick work.
No professions, global order board, message reward, or learned payload scheduler.
Each independent trajectory needs a unique run_id; IDs never enter actor input.
"""
from dataclasses import dataclass, field
import math
import random
import re

SCHEMA = "hearthbound.distributed-demand.v0.2"
ACTIONS = ("WAIT", "GO_DEPOT", "GO_WORKSHOP_1", "GO_WORKSHOP_2", "PICK_A",
           "PICK_B", "DROP", "WORK", "SHARE")
FEATURES = ("time_remaining", "idle", "cargo_a", "cargo_b", "travel_cost",
            "local_peers", "local_workers", "shareable", "at_depot", "depot_travel",
            "depot_known", "depot_a", "depot_b", "depot_age", "depot_report") + tuple(
    f"workshop_{node}_{name}" for node in (1, 2) for name in
    ("at", "travel", "known", "stock_a", "stock_b", "need_a", "need_b",
     "order_age", "deadline_remaining", "age", "report"))
F = {name: i for i, name in enumerate(FEATURES)}
PROTOCOLS = ("local", "no_messages", "unread", "instant", "no_relay")
DEMAND_REGIMES = ("recurring", "shutdown")
COORDINATES = (0, -3, 4)
PERIOD, ORDER_LIFETIME, WORK_TICKS, TTL, CAPACITY = 28, 24, 2, 24, 8
MAX_HOPS = 8


def mask(observation):
    """Only published current local state gates capabilities; races remain possible."""
    if len(observation) != len(FEATURES) or any(
            not math.isfinite(x) or not 0 <= x <= 1 for x in observation):
        raise ValueError("Invalid distributed-demand observation")
    active = observation[F["time_remaining"]] > 0 and observation[F["idle"]] == 1
    cargo = observation[F["cargo_a"]] + observation[F["cargo_b"]] > 0
    at = [observation[F["at_depot"]] == 1] + [
        observation[F[f"workshop_{n}_at"]] == 1 for n in (1, 2)]
    work = drop = False
    for n in (1, 2):
        if at[n]:
            for kind in ("a", "b"):
                stock = observation[F[f"workshop_{n}_stock_{kind}"]]
                need = observation[F[f"workshop_{n}_need_{kind}"]]
                work |= stock > 0 and need > 0
                drop |= observation[F[f"cargo_{kind}"]] > 0 and stock < 1
    return ((True,) + tuple(active and not here for here in at) + (
        active and at[0] and not cargo and observation[F["depot_a"]] > 0,
        active and at[0] and not cargo and observation[F["depot_b"]] > 0,
        active and drop, active and work,
        active and observation[F["shareable"]] > 0 and observation[F["local_peers"]] > 0))


@dataclass(frozen=True)
class Evidence:
    observation_id: str
    node: int
    payload: tuple
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
class Order:
    order_id: str
    node: int
    kind: int
    issued: int
    deadline: int
    remaining: int


@dataclass
class Citizen:
    node: int
    travel_cost: float
    task: str | None = None
    remaining: int = 0
    target: int | None = None
    cargo: int | None = None
    reservation: tuple | None = None
    direct: dict = field(default_factory=dict)
    reports: dict = field(default_factory=dict)
    attempted: dict = field(default_factory=dict)
    last_shared: dict = field(default_factory=dict)
    last_trip: dict | None = None


class Env:
    """All workers can supply, produce, inspect and communicate; none has a job ID.

    Orders expire only unreserved units. A work reservation contains its physical
    input and completes after two ticks even if the order's deadline passes.
    Shutdown suppresses future arrivals after horizon//2; existing orders drain.
    'instant' publishes current remote information explicitly, never as DIRECT.
    """
    def __init__(self, seed, agents=4, horizon=160, communication="local",
                 demand="recurring", trace=False, run_id=None):
        if type(seed) is not int or type(agents) is not int or not 1 <= agents <= 100:
            raise ValueError("Invalid seed/agent count")
        if type(horizon) is not int or not 1 <= horizon <= 10000:
            raise ValueError("Invalid horizon")
        if communication not in PROTOCOLS or demand not in DEMAND_REGIMES:
            raise ValueError("Unknown communication or demand regime")
        run_id = f"manual:{demand}:{communication}" if run_id is None else run_id
        if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,256}", run_id):
            raise ValueError("Invalid bounded run_id")
        self.seed, self.agents, self.horizon = seed, agents, horizon
        self.communication, self.demand, self.trace = communication, demand, bool(trace)
        self.world_id, self.run_id = f"synthetic-demand-{seed}", run_id
        self._scope = f"{self.world_id}:run:{run_id}"
        self.tick, self.done, self.events = 0, False, []
        self.shutdown_tick = horizon // 2
        self.quiet_after = self.shutdown_tick + ORDER_LIFETIME + WORK_TICKS
        self._initial = max(64, 8 * (horizon // PERIOD + 1))
        self._depot, self._stocks, self._consumed = [self._initial] * 2, [[0, 0] for _ in range(3)], [0, 0]
        starts = ([0, 1, 2] + [0] * (agents - 3)) if agents >= 3 else list(range(agents))
        random.Random(f"dd-starts:{seed}").shuffle(starts)
        trait_rng = random.Random(f"dd-traits:{seed}")
        self._agents = [Citizen(n, trait_rng.uniform(.5, 1.)) for n in starts]
        self.initial_nodes = tuple(starts)
        priority = random.Random(f"dd-priority:{seed}")
        self._priorities = [priority.sample(range(agents), agents) for _ in range(horizon)]
        self._schedule, self._orders = {}, []
        for node in (1, 2):
            rng = random.Random(f"dd-orders:{seed}:{node}")
            for at in range(0, horizon, PERIOD):
                self._schedule.setdefault(at, []).append((node, rng.randrange(2), rng.randint(2, 4)))
        self._counters = {name: 0 for name in (
            "produced", "demand_issued", "demand_expired", "late_completed", "attempts",
            "delivered", "forwarded", "cross_site_deliveries", "read_report_inputs",
            "report_present_for_travel", "blocked", "duplicates", "stale", "expired",
            "loop_rejected", "pickups", "drops", "pickup_denials", "drop_denials",
            "work_denials", "work_started", "work_ticks", "travel_ticks", "empty_trips",
            "loaded_trips", "empty_travel_ticks", "loaded_travel_ticks", "decisions",
            "empty_trips_with_report_delivery", "loaded_trips_with_report_delivery",
            "drops_without_current_need")}
        self._per_agent = [{name: 0 for name in (
            "produced", "shares", "deliveries", "forwarded", "cross_site_deliveries",
            "received", "read_report_inputs", "pickups", "drops", "work_ticks",
            "travel_ticks", "empty_trips", "loaded_trips", "empty_travel_ticks",
            "loaded_travel_ticks", "decisions", "personal_reward",
            "empty_trips_with_report_delivery", "loaded_trips_with_report_delivery",
            "drops_without_current_need")} for _ in range(agents)]
        self._phases = {phase: {name: 0 for name in (
            "produced", "attempts", "work_ticks", "travel_ticks", "empty_travel_ticks",
            "loaded_travel_ticks", "empty_trips", "loaded_trips",
            "empty_trips_with_report_delivery", "loaded_trips_with_report_delivery",
            "drops_without_current_need")} for phase in ("early", "late", "quiet")}
        self._arrivals()
        self._refresh_local()

    def _emit(self, event, **fields):
        if self.trace:
            self.events.append(dict(world_id=self.world_id, run_id=self.run_id,
                                    tick=self.tick, event=event, **fields))

    def _bump(self, name, amount=1, agent=None):
        self._counters[name] += amount
        if agent is not None and name in self._per_agent[agent]:
            self._per_agent[agent][name] += amount
        for phase in (("early",) if self.tick < self.shutdown_tick else ("late",)) + (
                ("quiet",) if self.tick >= self.quiet_after else ()):
            if name in self._phases[phase]:
                self._phases[phase][name] += amount

    def _agent(self, i):
        if type(i) is not int or not 0 <= i < self.agents:
            raise ValueError("Unknown citizen")
        return self._agents[i]

    def ready(self):
        return [] if self.done else [i for i, a in enumerate(self._agents) if a.task is None]

    def _arrivals(self):
        if self.demand == "shutdown" and self.tick >= self.shutdown_tick:
            return
        for node, kind, quantity in self._schedule.get(self.tick, ()):
            order = Order(f"{self._scope}:order:{node}:{self.tick}", node, kind,
                          self.tick, self.tick + ORDER_LIFETIME, quantity)
            self._orders.append(order)
            self._bump("demand_issued", quantity)
            self._emit("ORDER_ISSUED", order_id=order.order_id, node=node, kind=kind,
                       quantity=quantity, deadline=order.deadline)

    def _payload(self, node):
        if node == 0:
            return tuple(self._depot)
        orders = [o for o in self._orders if o.node == node and o.remaining > 0]
        need = [sum(o.remaining for o in orders if o.kind == k) for k in (0, 1)]
        issued = min((o.issued for o in orders), default=self.tick)
        deadline = min((o.deadline for o in orders), default=self.tick)
        return (*self._stocks[node], *need, issued, deadline)

    def _fresh(self, entry):
        return entry is not None and 0 <= self.tick - entry.evidence.observed_tick <= TTL

    def _knowledge(self, i, node, sealed=False):
        actor = self._agent(i)
        if self.communication == "instant" and not sealed:
            return Knowledge(Evidence(f"{self._scope}:public:{node}:{self.tick}", node,
                                      self._payload(node), self.tick, -1), "PUBLIC")
        own, report = actor.direct.get(node), actor.reports.get(node)
        own = own if self._fresh(own) else None
        report = report if self._fresh(report) and (sealed or self.communication != "unread") else None
        if own is None:
            return report
        return own if report is None or own.evidence.observed_tick >= report.evidence.observed_tick else report

    def _peers(self, i):
        actor = self._agent(i)
        return [j for j, other in enumerate(self._agents) if i != j
                and actor.task is None and other.task != "TRAVEL" and actor.node == other.node]

    def _share(self, i):
        actor, peers, candidates = self._agent(i), self._peers(i), []
        for node in range(3):
            # Everyone at the encounter has current direct sight of this node.
            if node == actor.node:
                continue
            entry = (actor.direct.get(node) if self.communication in ("no_relay", "instant")
                     else self._knowledge(i, node, sealed=True))
            if not self._fresh(entry) or len(entry.route) >= MAX_HOPS:
                continue
            recipients = [j for j in peers if actor.attempted.get((node, j)) != entry.evidence.observation_id]
            if recipients:
                candidates.append((actor.last_shared.get(node, -1), node, entry, recipients))
        return min(candidates, key=lambda x: (x[0], x[1]))[2:] if candidates else (None, [])

    def obs(self, i):
        actor = self._agent(i)
        idle = actor.task is None
        depot = self._knowledge(i, 0)
        workers = (sum(a.node == actor.node and a.task == "WORK" for a in self._agents)
                   if actor.task != "TRAVEL" else 0)
        values = [max(0, self.horizon - self.tick) / self.horizon, float(idle),
                  float(actor.cargo == 0), float(actor.cargo == 1), actor.travel_cost,
                  len(self._peers(i)) / max(1, self.agents - 1), workers / self.agents,
                  float(self._share(i)[0] is not None), float(idle and actor.node == 0),
                  abs(COORDINATES[actor.node]) / 7., float(depot is not None),
                  depot.evidence.payload[0] / self._initial if depot else 0.,
                  depot.evidence.payload[1] / self._initial if depot else 0.,
                  (self.tick - depot.evidence.observed_tick) / TTL if depot else 1.,
                  float(depot is not None and depot.origin == "REPORT")]
        for node in (1, 2):
            entry = self._knowledge(i, node)
            stock_a, stock_b, need_a, need_b, issued, deadline = entry.evidence.payload if entry else (0, 0, 0, 0, self.tick, self.tick)
            values.extend((float(idle and actor.node == node),
                abs(COORDINATES[actor.node] - COORDINATES[node]) / 7., float(entry is not None),
                stock_a / CAPACITY, stock_b / CAPACITY, need_a / 4., need_b / 4.,
                min(1., max(0, self.tick - issued) / ORDER_LIFETIME),
                min(1., max(0, deadline - self.tick) / ORDER_LIFETIME),
                (self.tick - entry.evidence.observed_tick) / TTL if entry else 1.,
                float(entry is not None and entry.origin == "REPORT")))
        return tuple(values)

    def _refresh_local(self):
        for i, actor in enumerate(self._agents):
            for memory in (actor.direct, actor.reports):
                for node, entry in list(memory.items()):
                    if not self._fresh(entry):
                        del memory[node]
                        self._bump("expired")
                        self._emit("MEMORY_EXPIRED", citizen=i, observation_id=entry.evidence.observation_id)
            if actor.task is not None:
                continue
            evidence = Evidence(f"{self._scope}:sight:{i}:{actor.node}:{self.tick}", actor.node,
                                self._payload(actor.node), self.tick, i)
            actor.direct[actor.node] = Knowledge(evidence, "DIRECT", route=(i,))
            self._emit("DIRECT_OBSERVATION", citizen=i, node=actor.node,
                       observation_id=evidence.observation_id, payload=evidence.payload)

    def _admit(self, recipient, sender, entry, message_id):
        actor, evidence = self._agent(recipient), entry.evidence
        if not self._fresh(entry):
            reason = "STALE"
        elif recipient in entry.route or len(entry.route) >= MAX_HOPS:
            reason = "LOOP"
        elif any(k and k.evidence.observation_id == evidence.observation_id
                 for k in (actor.direct.get(evidence.node), actor.reports.get(evidence.node))):
            reason = "DUPLICATE"
        elif any(k and k.evidence.observed_tick >= evidence.observed_tick
                 for k in (actor.direct.get(evidence.node), actor.reports.get(evidence.node))):
            reason = "SUPERSEDED"
        else:
            reason = None
        if reason:
            self._bump({"STALE": "stale", "LOOP": "loop_rejected", "DUPLICATE": "duplicates", "SUPERSEDED": "stale"}[reason])
            self._emit("REPORT_REJECTED", reason=reason, recipient=recipient, sender=sender, message_id=message_id)
            return False
        actor.reports[evidence.node] = Knowledge(evidence, "REPORT", sender,
                                                entry.route + (recipient,), message_id)
        forwarded = sender != evidence.observer
        self._bump("delivered")
        self._bump("forwarded", int(forwarded), sender)
        self._bump("cross_site_deliveries", 1, sender)
        self._per_agent[sender]["deliveries"] += 1
        self._per_agent[recipient]["received"] += 1
        trip = self._agents[sender].last_trip
        carried = (trip is not None and trip["end_tick"] is not None
                   and trip["destination"] == self._agents[sender].node
                   and evidence.observation_id in trip["held_observation_ids"])
        if carried and not trip["credited"]:
            self._bump("loaded_trips_with_report_delivery" if trip["loaded"]
                       else "empty_trips_with_report_delivery", agent=sender)
            trip["credited"] = True
        self._emit("REPORT_DELIVERED", sender=sender, recipient=recipient, message_id=message_id,
                   parent_message_id=entry.message_id, observation_id=evidence.observation_id,
                   source_node=evidence.node, original_observer=evidence.observer,
                   observed_tick=evidence.observed_tick, payload=evidence.payload,
                   encounter_node=self._agents[sender].node, route=entry.route + (recipient,), forwarded=forwarded,
                   carrying_trip_id=trip["trip_id"] if carried else None)
        return True

    def step(self, actions):
        if self.done or not isinstance(actions, dict) or any(type(i) is not int for i in actions):
            raise ValueError("Invalid actions or finished episode")
        ready = self.ready()
        if set(actions) != set(ready):
            raise ValueError("Supply exactly all ready citizens' simultaneous actions")
        snapshots = {i: self.obs(i) for i in ready}
        if any(type(actions[i]) is not int or not 0 <= actions[i] < len(ACTIONS)
               or not mask(snapshots[i])[actions[i]] for i in ready):
            raise ValueError("Action outside published local capability mask")
        sends = [(i, *self._share(i)) for i in ready if actions[i] == 8]
        personal = [-.002] * self.agents
        for i in ready:
            self._bump("decisions", agent=i)
            for node in range(3):
                entry = self._knowledge(i, node)
                if entry and entry.origin == "REPORT":
                    self._bump("read_report_inputs", agent=i)
                    self._emit("REPORT_POLICY_INPUT", citizen=i, action=ACTIONS[actions[i]],
                               observation_id=entry.evidence.observation_id, message_id=entry.message_id)
                    if actions[i] == node + 1:
                        self._bump("report_present_for_travel")
        for sender, payload, recipients in sends:
            personal[sender] -= .01
            self._bump("attempts")
            self._per_agent[sender]["shares"] += 1
            actor = self._agents[sender]
            message = f"{self._scope}:send:{self.tick}:{sender}"
            actor.last_shared[payload.evidence.node] = self.tick
            self._emit("REPORT_SENT", sender=sender, recipients=recipients, message_id=message,
                       observation_id=payload.evidence.observation_id, payload=payload.evidence.payload,
                       original_observer=payload.evidence.observer, observed_tick=payload.evidence.observed_tick,
                       source_node=payload.evidence.node, parent_message_id=payload.message_id)
            for recipient in recipients:
                actor.attempted[(payload.evidence.node, recipient)] = payload.evidence.observation_id
                if self.communication == "no_messages":
                    self._bump("blocked")
                    self._emit("TRANSPORT_BLOCKED", sender=sender, recipient=recipient, message_id=message)
                else:
                    self._admit(recipient, sender, payload, message)
        for i in self._priorities[self.tick]:
            if i not in actions:
                continue
            actor, action = self._agents[i], actions[i]
            if 1 <= action <= 3:
                actor.task, actor.target = "TRAVEL", action - 1
                actor.remaining = abs(COORDINATES[actor.node] - COORDINATES[actor.target])
                held = tuple(sorted({k.evidence.observation_id for memory in (actor.direct, actor.reports)
                                     for k in memory.values() if self._fresh(k)}))
                actor.last_trip = dict(trip_id=f"{self._scope}:trip:{self.tick}:{i}", source=actor.node,
                    destination=actor.target, start_tick=self.tick, end_tick=None,
                    loaded=actor.cargo is not None, held_observation_ids=held, credited=False)
                self._bump("empty_trips" if actor.cargo is None else "loaded_trips", agent=i)
                self._emit("TRAVEL_STARTED", citizen=i, source=actor.node, target=actor.target,
                           duration=actor.remaining, cargo=actor.cargo, trip_id=actor.last_trip["trip_id"],
                           held_observation_ids=held)
            elif action in (4, 5):
                kind = action - 4
                if self._depot[kind] == 0:
                    self._bump("pickup_denials")
                    personal[i] -= .01
                else:
                    self._depot[kind] -= 1
                    actor.cargo = kind
                    self._bump("pickups", agent=i)
                    personal[i] -= .002
                    self._emit("PICKUP", citizen=i, kind=kind)
            elif action == 6:
                if self._stocks[actor.node][actor.cargo] == CAPACITY:
                    self._bump("drop_denials")
                    personal[i] -= .01
                else:
                    kind = actor.cargo
                    need = sum(o.remaining for o in self._orders if o.node == actor.node and o.kind == kind)
                    if need <= self._stocks[actor.node][kind]:
                        self._bump("drops_without_current_need", agent=i)
                    self._stocks[actor.node][kind] += 1
                    actor.cargo = None
                    self._bump("drops", agent=i)
                    personal[i] -= .002
                    self._emit("DROP", citizen=i, node=actor.node, kind=kind)
            elif action == 7:
                candidates = [o for o in self._orders if o.node == actor.node and o.remaining > 0
                              and self._stocks[actor.node][o.kind] > 0]
                if not candidates:
                    self._bump("work_denials")
                    personal[i] -= .01
                else:
                    order = min(candidates, key=lambda o: (o.deadline, o.order_id))
                    order.remaining -= 1
                    self._stocks[actor.node][order.kind] -= 1
                    actor.task, actor.remaining = "WORK", WORK_TICKS
                    actor.reservation = (order.order_id, order.kind, order.deadline)
                    self._bump("work_started")
                    self._emit("WORK_RESERVED", citizen=i, node=actor.node, order_id=order.order_id,
                               kind=order.kind, quantity=1, duration=WORK_TICKS)
        products = 0
        for i, actor in enumerate(self._agents):
            if actor.task == "TRAVEL":
                self._bump("travel_ticks", agent=i)
                self._bump("empty_travel_ticks" if actor.cargo is None else "loaded_travel_ticks", agent=i)
                personal[i] -= .004 * actor.travel_cost
            elif actor.task == "WORK":
                self._bump("work_ticks", agent=i)
                personal[i] -= .003
            if actor.task:
                actor.remaining -= 1
                if actor.remaining == 0:
                    if actor.task == "TRAVEL":
                        actor.node, actor.target = actor.target, None
                        actor.last_trip["end_tick"] = self.tick + 1
                        self._emit("TRAVEL_ARRIVED", citizen=i, node=actor.node, effective_tick=self.tick + 1,
                                   trip_id=actor.last_trip["trip_id"])
                    else:
                        order_id, kind, deadline = actor.reservation
                        self._consumed[kind] += 1
                        products += 1
                        self._bump("produced", agent=i)
                        self._bump("late_completed", int(self.tick + 1 > deadline))
                        self._emit("PRODUCT_VERIFIED", citizen=i, node=actor.node, order_id=order_id,
                                   consumed_kind=kind, quantity=1, effective_tick=self.tick + 1)
                        actor.reservation = None
                    actor.task = None
            self._per_agent[i]["personal_reward"] += personal[i]
        self.tick += 1
        for order in self._orders:
            if order.remaining and self.tick >= order.deadline:
                self._bump("demand_expired", order.remaining)
                self._emit("ORDER_EXPIRED", order_id=order.order_id, node=order.node,
                           kind=order.kind, quantity=order.remaining)
                order.remaining = 0
        self._arrivals()
        self._refresh_local()
        self.done = self.tick >= self.horizon
        return float(products), personal, self.done

    def metrics(self):
        cargo = [sum(a.cargo == k for a in self._agents) for k in (0, 1)]
        wip = [sum(a.reservation is not None and a.reservation[1] == k for a in self._agents) for k in (0, 1)]
        stocks = [sum(self._stocks[n][k] for n in (1, 2)) for k in (0, 1)]
        residual = [self._initial - self._depot[k] - stocks[k] - cargo[k] - wip[k] - self._consumed[k] for k in (0, 1)]
        pending = sum(o.remaining for o in self._orders)
        return dict(self._counters, conservation_residual_A=residual[0], conservation_residual_B=residual[1],
                    conservation_residual=sum(residual), demand_pending=pending, demand_reserved=sum(wip),
                    demand_residual=self._counters["demand_issued"] - self._counters["produced"]
                        - self._counters["demand_expired"] - pending - sum(wip),
                    initial_A=self._initial, initial_B=self._initial, depot_A=self._depot[0], depot_B=self._depot[1],
                    workshop_A=stocks[0], workshop_B=stocks[1], cargo_A=cargo[0], cargo_B=cargo[1],
                    work_in_progress_A=wip[0], work_in_progress_B=wip[1], consumed_A=self._consumed[0],
                    consumed_B=self._consumed[1], initial_nodes=self.initial_nodes, tick=self.tick, horizon=self.horizon,
                    per_agent=[dict(x) for x in self._per_agent], phase_counts={k: dict(v) for k, v in self._phases.items()},
                    shutdown_tick=self.shutdown_tick, quiet_after=self.quiet_after, minecraft_worlds=0)


def scripted_local(observation):
    """Same observation-only work heuristic for every citizen; no fixed role IDs.

    Remote shortage reports can change the chosen cargo and destination. Sharing
    has a declared scripted priority before travel, not a claim of learned jobs.
    """
    valid = mask(observation)
    if valid[7]:
        return 7
    if valid[6]:
        return 6
    if valid[8]:
        return 8
    cargo = 0 if observation[F["cargo_a"]] else 1 if observation[F["cargo_b"]] else None
    candidates = []
    for node in (1, 2):
        known = observation[F[f"workshop_{node}_known"]]
        alive = observation[F[f"workshop_{node}_deadline_remaining"]] > 0
        for kind, letter in enumerate(("a", "b")):
            deficit = max(0., observation[F[f"workshop_{node}_need_{letter}"]] * 4
                          - observation[F[f"workshop_{node}_stock_{letter}"]] * CAPACITY) if alive else 0.
            if cargo is not None and kind != cargo:
                continue
            distance = observation[F[f"workshop_{node}_travel"]]
            candidates.append((0 if deficit > 0 else 1 if not known else 2,
                               -deficit, distance, node, kind))
    if cargo is not None:
        choices = [x for x in candidates if valid[x[3] + 1]]
        return min(choices)[3] + 1 if choices else 0
    if observation[F["at_depot"]]:
        needs = [x for x in candidates if x[0] == 0 and valid[x[4] + 4]]
        if needs:
            return min(needs)[4] + 4
        unknown = [x for x in candidates if x[0] == 1 and valid[x[3] + 1]]
        return min(unknown)[3] + 1 if unknown else 0
    if any(x[0] == 0 for x in candidates) and valid[1]:
        return 1
    unknown = [x for x in candidates if x[0] == 1 and valid[x[3] + 1]]
    return min(unknown)[3] + 1 if unknown else 0
