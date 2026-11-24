"""Selective report topics over frozen v0.2 physics. SYNTHETIC, not Forge.

Actors choose whether to share and which known topic to send. They cannot inspect
private recipient memories. The global physical features exposed by critic_state
are training-only; actor_obs remains local and remembers only its own last action.
"""
import copy
import math
import re

from distributed_demand_env import (
    ACTIONS as BASE_ACTIONS, CAPACITY, COORDINATES, DEMAND_REGIMES,
    FEATURES as BASE_FEATURES, F as BASE_F, MAX_HOPS, ORDER_LIFETIME,
    PROTOCOLS, TTL, Env as BaseEnv, mask as base_mask,
    scripted_local as base_scripted_local,
)


SCHEMA = "hearthbound.selective-communication.v0.3"
ACTIONS = BASE_ACTIONS[:8] + ("SHARE_DEPOT", "SHARE_WORKSHOP_1", "SHARE_WORKSHOP_2")
FEATURES = BASE_FEATURES + tuple(f"topic_available_{n}" for n in range(3)) + tuple(
    f"previous_action_{a}" for a in range(len(ACTIONS))) + ("previous_decision_elapsed",)
F = {name: i for i, name in enumerate(FEATURES)}
GLOBAL_FEATURES = ("global_depot_a", "global_depot_b") + tuple(
    f"global_workshop_{n}_{name}" for n in (1, 2) for name in
    ("stock_a", "stock_b", "need_a", "need_b", "order_age", "deadline_remaining")) + tuple(
    f"global_site_{n}_{name}" for n in range(3) for name in
    ("stationary", "working", "inbound", "cargo_a", "cargo_b", "inbound_cargo_a", "inbound_cargo_b"))
CRITIC_FEATURES = FEATURES + GLOBAL_FEATURES
MAX_DECISION_DURATION = max(COORDINATES) - min(COORDINATES)


def mask(observation):
    """Capabilities depend only on the published actor vector, including packets."""
    if len(observation) != len(FEATURES) or any(
            not math.isfinite(x) or not 0 <= x <= 1 for x in observation):
        raise ValueError("Invalid selective-communication observation")
    physical = base_mask(observation[:len(BASE_FEATURES)])
    return physical[:8] + tuple(
        physical[8] and observation[F[f"topic_available_{n}"]] > 0 for n in range(3))


class Env(BaseEnv):
    """The supplied map, orders, production, costs and material ledgers stay fixed.

    ``obs`` intentionally retains the parent 37-feature contract for the frozen
    physics' capability checks. Learned actors must use ``actor_obs``. A topic
    action sends the corresponding retained snapshot to eligible local peers;
    the actor does not get a recipient's knowledge or an estimate of its benefit.
    In the fixed-dispatch intervention, any legal topic command invokes the
    original scheduler instead. Inputs and masks are unchanged. Previous action
    remains the actor's requested command; metrics distinguish actual dispatch.

    Read suppression is an evaluation intervention. Existing readable memories
    can be retained while later packets remain available for sealed transport.
    A fork retains prefix evidence and orders with their original IDs, and gives
    new events/evidence the new run scope. It does not pretend prefix evidence
    was first observed in the fork.
    """
    def __init__(self, *args, dispatch_mode="selected", **kwargs):
        if dispatch_mode not in ("selected", "fixed"):
            raise ValueError("Unknown report dispatch mode")
        self.dispatch_mode = dispatch_mode
        self._selected_topics = {}
        self._selected_actions = {}
        self._suppressed_recipients = set()
        self._retained_readable = {}
        super().__init__(*args, **kwargs)
        self._previous_actions = [None] * self.agents
        self._previous_decision_ticks = [None] * self.agents
        self._topic_counts = [0, 0, 0]
        self._requested_topic_counts = [0, 0, 0]
        self._topic_per_agent = [[0, 0, 0] for _ in range(self.agents)]
        self._topic_phases = {phase: [0, 0, 0] for phase in ("early", "late", "quiet")}
        self.fork_parent = None

    def _readable_report(self, i, node):
        if self.communication == "unread":
            return None
        if i in self._suppressed_recipients:
            entry = self._retained_readable.get(i, {}).get(node)
        else:
            entry = self._agent(i).reports.get(node)
        return entry if self._fresh(entry) else None

    def _knowledge(self, i, node, sealed=False):
        if sealed or i not in self._suppressed_recipients or self.communication == "instant":
            return super()._knowledge(i, node, sealed=sealed)
        own, report = self._agent(i).direct.get(node), self._readable_report(i, node)
        own = own if self._fresh(own) else None
        if own is None:
            return report
        return own if report is None or own.evidence.observed_tick >= report.evidence.observed_tick else report

    def _topic(self, i, node):
        actor, peers = self._agent(i), self._peers(i)
        if node == actor.node:
            return None, []
        entry = (actor.direct.get(node) if self.communication in ("no_relay", "instant")
                 else self._knowledge(i, node, sealed=True))
        if not self._fresh(entry) or len(entry.route) >= MAX_HOPS:
            return None, []
        recipients = [j for j in peers
                      if actor.attempted.get((node, j)) != entry.evidence.observation_id]
        return (entry, recipients) if recipients else (None, [])

    def _share(self, i):
        if i in self._selected_topics and self.dispatch_mode == "selected":
            return self._topic(i, self._selected_topics[i])
        return super()._share(i)

    def _emit(self, event, **fields):
        if event == "REPORT_POLICY_INPUT":
            action = self._selected_actions.get(fields.get("citizen"))
            if action is not None:
                fields["action"] = ACTIONS[action]
        if event == "REPORT_SENT":
            action = self._selected_actions.get(fields.get("sender"))
            if action is not None:
                fields["requested_topic"] = action - 8
                fields["dispatch_mode"] = self.dispatch_mode
        super()._emit(event, **fields)

    def actor_obs(self, i):
        """Local beliefs, packet availability, and the actor's previous command."""
        self._agent(i)
        previous = self._previous_actions[i]
        at = self._previous_decision_ticks[i]
        elapsed = 0. if at is None else min(1., max(0, self.tick - at) / MAX_DECISION_DURATION)
        return self.obs(i) + tuple(float(self._topic(i, n)[0] is not None) for n in range(3)) + tuple(
            float(previous == a) for a in range(len(ACTIONS))) + (elapsed,)

    def critic_state(self, i):
        """Privileged *current* physical state; never call this inside an actor."""
        values = list(self.actor_obs(i)) + [n / self._initial for n in self._depot]
        for node in (1, 2):
            a, b, need_a, need_b, issued, deadline = self._payload(node)
            values.extend((a / CAPACITY, b / CAPACITY, need_a / 4., need_b / 4.,
                min(1., max(0, self.tick - issued) / ORDER_LIFETIME),
                min(1., max(0, deadline - self.tick) / ORDER_LIFETIME)))
        for node in range(3):
            stationary = [a for a in self._agents if a.task != "TRAVEL" and a.node == node]
            incoming = [a for a in self._agents if a.task == "TRAVEL" and a.target == node]
            values.extend(n / self.agents for n in (
                len(stationary), sum(a.task == "WORK" for a in stationary), len(incoming),
                sum(a.cargo == 0 for a in stationary), sum(a.cargo == 1 for a in stationary),
                sum(a.cargo == 0 for a in incoming), sum(a.cargo == 1 for a in incoming)))
        return tuple(values)

    def set_report_read_suppression(self, recipients, *, future_only=True):
        """Replace the suppressed recipient set, with no transport/cost changes.

        When future_only is true, each recipient keeps its currently readable
        reports until their original TTL expires, even if new sealed arrivals
        overwrite its transport inbox. With false, all report contents are hidden.
        Direct observations remain readable in both cases. Calling this method
        is an evaluator intervention, not an available policy action.
        """
        try:
            recipients = set(recipients)
        except TypeError as error:
            raise ValueError("Recipients must be an iterable of citizen IDs") from error
        if type(future_only) is not bool:
            raise ValueError("future_only must be a boolean")
        for i in recipients:
            self._agent(i)
        retained = {i: {n: entry for n in range(3)
                        if (entry := self._readable_report(i, n)) is not None}
                    if future_only else {} for i in recipients}
        self._suppressed_recipients = recipients
        self._retained_readable = retained
        self._emit("REPORT_READ_INTERVENTION", recipients=sorted(recipients),
                   future_only=future_only)

    def fork(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,256}", run_id):
            raise ValueError("Invalid bounded fork run_id")
        if run_id == self.run_id or self._selected_topics:
            raise ValueError("Fork needs a new run ID outside an active step")
        fork = copy.deepcopy(self)
        fork.fork_parent = dict(world_id=self.world_id, run_id=self.run_id, tick=self.tick)
        fork.run_id = run_id
        fork._scope = f"{fork.world_id}:run:{run_id}"
        fork._emit("WORLD_FORKED", parent_world_id=self.world_id,
                   parent_run_id=self.run_id, parent_tick=self.tick)
        return fork

    def step(self, actions):
        if self.done or not isinstance(actions, dict) or any(type(i) is not int for i in actions):
            raise ValueError("Invalid actions or finished episode")
        ready = self.ready()
        if set(actions) != set(ready):
            raise ValueError("Supply exactly all ready citizens' simultaneous actions")
        if any(type(actions[i]) is not int or not 0 <= actions[i] < len(ACTIONS)
               or not mask(self.actor_obs(i))[actions[i]] for i in ready):
            raise ValueError("Action outside published local capability mask")
        # The entire joint action is validated before previous actions or topic
        # records change. The parent captures every send before admitting any.
        tick = self.tick
        self._selected_actions = dict(actions)
        self._selected_topics = {i: a - 8 for i, a in actions.items() if a >= 8}
        dispatched = {i: self._share(i)[0].evidence.node for i in self._selected_topics}
        try:
            result = super().step({i: min(a, 8) for i, a in actions.items()})
        finally:
            self._selected_topics = {}
            self._selected_actions = {}
        for i, action in actions.items():
            self._previous_actions[i] = action
            self._previous_decision_ticks[i] = tick
            if action >= 8:
                self._requested_topic_counts[action - 8] += 1
                node = dispatched[i]
                self._topic_counts[node] += 1
                self._topic_per_agent[i][node] += 1
                phases = (("early",) if tick < self.shutdown_tick else ("late",)) + (
                    ("quiet",) if tick >= self.quiet_after else ())
                for phase in phases:
                    self._topic_phases[phase][node] += 1
        return result

    def metrics(self):
        return dict(super().metrics(), chosen_topics=list(self._topic_counts),
                    requested_topics=list(self._requested_topic_counts), dispatch_mode=self.dispatch_mode,
                    chosen_topics_per_agent=[list(row) for row in self._topic_per_agent],
                    chosen_topics_by_phase={k: list(v) for k, v in self._topic_phases.items()},
                    read_suppressed_recipients=sorted(self._suppressed_recipients),
                    fork_parent=copy.deepcopy(self.fork_parent))


def scripted_local(observation):
    """Parent heuristic with an explicit fixed topic order; this is a script."""
    valid = mask(observation)
    action = base_scripted_local(observation[:len(BASE_FEATURES)])
    return next((a for a in range(8, len(ACTIONS)) if valid[a]), 0) if action == 8 else action
