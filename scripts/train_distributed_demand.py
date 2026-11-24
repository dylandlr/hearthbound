#!/usr/bin/env python3
"""Shared-independent Double-DQN pilot for recurring distributed work. SYNTHETIC ONLY.

The actor reads bounded private belief features, not a privileged world state.
Global production is a training reward, not a policy input. This is neither a
centralized-critic algorithm nor a recurrent network. No occupation is assigned.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import random

import numpy as np

from distributed_demand_env import ACTIONS, FEATURES, SCHEMA as OBSERVATION_SCHEMA
from distributed_demand_env import Env, mask, scripted_local


SCHEMA = "hearthbound.distributed-demand-learning.v0.1"
GAMMA = .98
PERSONAL_WEIGHT = .25
COMMUNICATION = ("local", "no_messages", "unread", "instant", "no_relay")
DEMANDS = ("recurring", "shutdown")
SLOTS = tuple(("trained", c) for c in COMMUNICATION) + tuple(
    (p, "local") for p in ("untrained", "scripted_local", "random")) + tuple(
    ("scripted_local", c) for c in ("no_messages", "unread", "instant"))
SETTINGS = dict(algorithm="shared-independent-Double-DQN", hidden_units=64,
    batch_size=32, replay_start=64, replay_capacity=20000, replay_trim=2000,
    target_update_interval=200, adam_rate=.001, epsilon_initial=.9,
    epsilon_final=.08, epsilon_decay_fraction=.8, updates_per_world_tick=1,
    gradient_norm_clip=5., huber_delta=1.)


def stable_seed(*parts):
    return int.from_bytes(hashlib.sha256(repr(parts).encode()).digest()[:8], "big")


def source_manifest():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ("distributed_demand_env.py", "train_distributed_demand.py")}


def observation_contract():
    return dict(schema=OBSERVATION_SCHEMA, features=list(FEATURES), actions=list(ACTIONS),
                source_manifest=source_manifest())


class Network:
    def __init__(self, seed, hidden=64):
        if type(hidden) is not int or not 1 <= hidden <= 256:
            raise ValueError("Invalid hidden width")
        rng = np.random.default_rng(seed)
        self.parameters = dict(
            w1=rng.normal(0, math.sqrt(2 / len(FEATURES)), (len(FEATURES), hidden)),
            b1=np.zeros(hidden), w2=rng.normal(0, .03, (hidden, len(ACTIONS))),
            b2=np.zeros(len(ACTIONS)))
        self.m = {k: np.zeros_like(v) for k, v in self.parameters.items()}
        self.v = {k: np.zeros_like(v) for k, v in self.parameters.items()}
        self.updates = 0

    def values(self, observations):
        p = self.parameters
        return np.maximum(np.asarray(observations) @ p["w1"] + p["b1"], 0) @ p["w2"] + p["b2"]

    def greedy(self, observation):
        return int(np.argmax(np.where(mask(observation), self.values(observation), -np.inf)))

    def digest(self):
        digest = hashlib.sha256()
        for name, value in sorted(self.parameters.items()):
            digest.update(name.encode())
            digest.update(repr(value.shape).encode())
            digest.update(value.astype("<f8").tobytes())
        return digest.hexdigest()

    def bellman_targets(self, batch, target):
        successor = np.asarray([t["next_observation"] for t in batch])
        available = np.asarray([mask(o) for o in successor])
        # Online masked argmax, target-network evaluation: Double-DQN.
        choices = np.argmax(np.where(available, self.values(successor), -np.inf), axis=1)
        future = target.values(successor)[np.arange(len(batch)), choices]
        terminal = np.asarray([t["terminal"] for t in batch], dtype=bool)
        rewards = np.asarray([t["discounted_reward"] for t in batch], dtype=float)
        durations = np.asarray([t["duration"] for t in batch])
        if np.any(durations < 1) or np.any(durations != durations.astype(int)):
            raise ValueError("Every transition must span positive integral ticks")
        expected = rewards + GAMMA ** durations * (~terminal) * future
        if not np.isfinite(expected).all():
            raise ValueError("Nonfinite target")
        return expected

    def loss_and_gradients(self, observations, actions, expected):
        """Huber loss; targets are held constant for the semi-gradient update."""
        x = np.asarray(observations)
        actions, expected = np.asarray(actions, dtype=int), np.asarray(expected)
        p = self.parameters
        z = x @ p["w1"] + p["b1"]
        hidden = np.maximum(z, 0)
        values = hidden @ p["w2"] + p["b2"]
        errors = values[np.arange(len(x)), actions] - expected
        if not np.isfinite(errors).all():
            raise ValueError("Nonfinite training error")
        absolute = np.abs(errors)
        loss = float(np.where(absolute <= 1, .5 * errors ** 2, absolute - .5).mean())
        dq = np.zeros_like(values)
        dq[np.arange(len(x)), actions] = np.clip(errors, -1, 1) / len(x)
        dh = (dq @ p["w2"].T) * (z > 0)
        gradients = dict(w2=hidden.T @ dq, b2=dq.sum(axis=0),
                         w1=x.T @ dh, b1=dh.sum(axis=0))
        return loss, gradients

    def update(self, batch, target, rate=SETTINGS["adam_rate"]):
        if not batch or not math.isfinite(rate) or rate <= 0:
            raise ValueError("Invalid learning batch/rate")
        for item in batch:
            if not mask(item["observation"])[item["action"]]:
                raise ValueError("Replay action violates its own observation mask")
        expected = self.bellman_targets(batch, target)
        loss, gradients = self.loss_and_gradients(
            [t["observation"] for t in batch], [t["action"] for t in batch], expected)
        norm = math.sqrt(sum(float(np.sum(g * g)) for g in gradients.values()))
        if not math.isfinite(norm):
            raise ValueError("Nonfinite gradient")
        self.updates += 1
        for name, gradient in gradients.items():
            gradient *= min(1., SETTINGS["gradient_norm_clip"] / max(norm, 1e-12))
            self.m[name] = .9 * self.m[name] + .1 * gradient
            self.v[name] = .999 * self.v[name] + .001 * gradient * gradient
            m = self.m[name] / (1 - .9 ** self.updates)
            v = self.v[name] / (1 - .999 ** self.updates)
            self.parameters[name] -= rate * m / (np.sqrt(v) + 1e-8)
        if not all(np.isfinite(p).all() for p in self.parameters.values()):
            raise ValueError("Nonfinite learned parameters")
        return loss

    def save(self, destination):
        data = dict(schema=SCHEMA, observation_contract=observation_contract(),
                    parameter_sha256=self.digest(),
                    parameters={k: v.tolist() for k, v in self.parameters.items()})
        Path(destination).write_text(json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n")

    @classmethod
    def load(cls, source):
        data = json.loads(Path(source).read_text())
        if data.get("schema") != SCHEMA or data.get("observation_contract") != observation_contract():
            raise ValueError("Checkpoint observation/action/source contract mismatch")
        parameters = {k: np.asarray(v, dtype=float) for k, v in data["parameters"].items()}
        if set(parameters) != {"w1", "b1", "w2", "b2"}:
            raise ValueError("Checkpoint parameter keys mismatch")
        hidden = parameters["b1"].size
        expected = dict(w1=(len(FEATURES), hidden), b1=(hidden,),
                        w2=(hidden, len(ACTIONS)), b2=(len(ACTIONS),))
        if not 1 <= hidden <= 256 or any(parameters[k].shape != shape
                or not np.isfinite(parameters[k]).all() for k, shape in expected.items()):
            raise ValueError("Invalid checkpoint tensor")
        model = cls(0, hidden)
        model.parameters = parameters
        if model.digest() != data.get("parameter_sha256"):
            raise ValueError("Checkpoint parameter digest mismatch")
        return model


def run_episode(policy, world, *, on_transition=None, on_tick=None, trace=False):
    """Continuous reward ledgers cover every actor, including while traveling."""
    pending, transitions, action_trace = {}, [], []
    colony_total, personal_totals = 0., [0.] * world.agents
    halves = [dict(action_counts={a: 0 for a in ACTIONS}, produced=0., personal_cost=0.)
              for _ in range(2)]

    def complete(agent, terminal):
        transition = pending.pop(agent)
        transition.update(next_observation=tuple(world.obs(agent)), terminal=terminal)
        if transition["duration"] < 1:
            raise AssertionError("Zero-length transition")
        transitions.append(transition)
        if on_transition:
            on_transition(transition)

    while not world.done:
        half = int(world.tick >= world.horizon // 2)
        ready = world.ready()
        observations = {a: tuple(world.obs(a)) for a in ready}
        actions = {}
        for agent in ready:
            if agent in pending:
                complete(agent, False)
            observation = observations[agent]
            action = int(policy(agent, observation))
            if not 0 <= action < len(ACTIONS) or not mask(observation)[action]:
                raise AssertionError("Policy violated published mask")
            actions[agent] = action
            halves[half]["action_counts"][ACTIONS[action]] += 1
            pending[agent] = dict(agent=agent, start_tick=world.tick,
                observation=observation, action=action, duration=0,
                discounted_reward=0., personal_reward=0., colony_reward=0.)
            if trace:
                action_trace.append(dict(tick=world.tick, agent=agent,
                                         action=ACTIONS[action], observation=observation))
        colony, personal, done = world.step(actions)
        if len(personal) != world.agents or not math.isfinite(colony) or not all(map(math.isfinite, personal)):
            raise AssertionError("Invalid reward ledger")
        if set(pending) != set(range(world.agents)):
            raise AssertionError("An agent has no active transition")
        colony_total += colony
        halves[half]["produced"] += colony
        halves[half]["personal_cost"] -= sum(personal)
        for agent, transition in pending.items():
            transition["discounted_reward"] += GAMMA ** transition["duration"] * (
                colony + PERSONAL_WEIGHT * personal[agent])
            transition["duration"] += 1
            transition["personal_reward"] += personal[agent]
            transition["colony_reward"] += colony
            personal_totals[agent] += personal[agent]
        if done:
            for agent in list(pending):
                complete(agent, True)
        if on_tick:
            on_tick()
    for agent in range(world.agents):
        own = [t for t in transitions if t["agent"] == agent]
        if (sum(t["duration"] for t in own) != world.horizon
                or [t["start_tick"] for t in own] != list(np.cumsum(
                    [0] + [t["duration"] for t in own[:-1]]))):
            raise AssertionError("Missing/overlapping actor ticks")
    metrics = world.metrics()
    if metrics["produced"] != colony_total:
        raise AssertionError("Colony reward differs from verified simulated products")
    if any(metrics[k] != 0 for k in ("conservation_residual_A", "conservation_residual_B")):
        raise AssertionError("Material conservation failed")
    if metrics["demand_residual"] != 0:
        raise AssertionError("Demand accounting failed")
    metrics.update(personal_reward=personal_totals, colony_reward=colony_total,
                   policy_decisions=len(transitions), activity_by_half=halves)
    carried = [r.get("cross_site_deliveries", 0) for r in metrics.get("per_agent", [])]
    total_carried = sum(carried)
    metrics.update(agents_with_cross_site_deliveries=sum(n > 0 for n in carried),
        cross_site_delivery_top_agent_fraction=max(carried) / total_carried if total_carried else None,
        cross_site_delivery_concentration=sum((n / total_carried) ** 2 for n in carried)
        if total_carried else None)
    if trace:
        metrics.update(action_trace=action_trace, world_events=copy.deepcopy(world.events))
    return metrics, transitions


def train(seed, episodes, *, agents=4, horizon=160, progress=None):
    """Alternate recurring/shutdown training worlds without exposing the label."""
    online = Network(seed)
    initial, target = copy.deepcopy(online), copy.deepcopy(online)
    explore = random.Random(stable_seed("demand-exploration", seed))
    sample = random.Random(stable_seed("demand-replay", seed))
    replay, losses, decisions, products = [], [], 0, 0
    world_digest = hashlib.sha256()
    by_demand = {d: dict(episodes=0, products=0) for d in DEMANDS}
    for episode in range(episodes):
        demand = DEMANDS[episode % len(DEMANDS)]
        world_seed = stable_seed("demand-training-world", seed, episode)
        world_digest.update(f"{world_seed}:{demand}\n".encode())
        epsilon = .08 + .82 * max(0., 1 - episode / max(1., episodes * .8))

        def policy(agent, observation):
            valid = [i for i, allowed in enumerate(mask(observation)) if allowed]
            return explore.choice(valid) if explore.random() < epsilon else online.greedy(observation)

        def remember(transition):
            replay.append(transition)
            if len(replay) > SETTINGS["replay_capacity"]:
                del replay[:SETTINGS["replay_trim"]]

        def learn():
            if len(replay) < SETTINGS["replay_start"]:
                return
            losses.append(online.update(sample.sample(replay, SETTINGS["batch_size"]), target))
            if online.updates % SETTINGS["target_update_interval"] == 0:
                target.parameters = {k: v.copy() for k, v in online.parameters.items()}

        metrics, transitions = run_episode(policy,
            Env(world_seed, agents=agents, horizon=horizon, communication="local", demand=demand,
                run_id=f"train:{seed}:{episode}:{demand}"),
            on_transition=remember, on_tick=learn)
        products += metrics["produced"]
        decisions += len(transitions)
        by_demand[demand]["episodes"] += 1
        by_demand[demand]["products"] += metrics["produced"]
        if progress and (episode + 1) % max(1, episodes // 4) == 0:
            progress(dict(training_seed=seed, episodes_completed=episode + 1,
                          optimizer_updates=online.updates, training_products=products))
    return online, initial, dict(episodes=episodes, world_ticks=episodes * horizon,
        agent_ticks=episodes * horizon * agents, decisions=decisions, training_products=products,
        optimizer_updates=online.updates, mean_huber_loss=float(np.mean(losses)) if losses else None,
        training_world_seed_manifest_sha256=world_digest.hexdigest(), by_demand=by_demand)


def evaluate(model, initial, world_seeds, *, agents=4, horizon=160, evaluation_scope="test"):
    if (not isinstance(evaluation_scope, str) or not evaluation_scope
            or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
                   for c in evaluation_scope) or len(evaluation_scope) > 32):
        raise ValueError("Evaluation scope must be 1..32 ASCII letters, digits, dot, dash or underscore")
    before = (model.digest(), initial.digest(), model.updates, initial.updates)
    rows, examples = [], {}
    for index, seed in enumerate(world_seeds):
        for demand in DEMANDS:
            for label, communication in SLOTS:
                rng = random.Random(stable_seed("demand-evaluation-random", seed))
                if label == "trained":
                    policy = lambda agent, observation: model.greedy(observation)
                elif label == "untrained":
                    policy = lambda agent, observation: initial.greedy(observation)
                elif label == "scripted_local":
                    policy = lambda agent, observation: scripted_local(observation)
                else:
                    policy = lambda agent, observation: rng.choice([
                        i for i, allowed in enumerate(mask(observation)) if allowed])
                run_id = f"eval:{evaluation_scope}:{seed}:{demand}:{label}:{communication}"
                row = dict(world_seed=seed, demand=demand, policy=label,
                           communication=communication, run_id=run_id)
                try:
                    metrics, _ = run_episode(policy,
                        Env(seed, agents=agents, horizon=horizon, communication=communication,
                            demand=demand, trace=index == 0, run_id=run_id), trace=index == 0)
                    if index == 0:
                        examples[f"{demand}:{label}:{communication}"] = dict(world_seed=seed,
                            run_id=run_id, action_trace=metrics.pop("action_trace"),
                            world_events=metrics.pop("world_events"))
                    row.update(status="valid", **metrics)
                except Exception as exc:
                    row.update(status="failed", error=f"{type(exc).__name__}: {exc}", produced=None)
                rows.append(row)
    if before != (model.digest(), initial.digest(), model.updates, initial.updates):
        raise AssertionError("Evaluation changed frozen weights or optimizer counters")
    return rows, examples


def crossed_interval(matrix, seed=9017, repeats=2000):
    """Exploratory resampling of training seeds and whole paired world seeds."""
    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2 or not np.isfinite(values).all() or min(values.shape) < 1:
        raise ValueError("Invalid complete crossed matrix")
    rng, means = np.random.default_rng(seed), []
    for _ in range(repeats):
        training = rng.integers(values.shape[0], size=values.shape[0])
        worlds = rng.integers(values.shape[1], size=values.shape[1])
        means.append(float(values[np.ix_(training, worlds)].mean()))
    return [float(x) for x in np.quantile(means, [.025, .975])]


def summarize(rows, seeds, worlds):
    lookup = {}
    for row in rows:
        key = (row["training_seed"], row["world_seed"], row["demand"],
               row["policy"], row["communication"])
        if key in lookup:
            raise ValueError("Duplicate evaluation slot")
        lookup[key] = row
    planned = len(seeds) * len(worlds)

    def paired(first, second, value=lambda row: row["produced"]):
        matrix = []
        for seed in seeds:
            line = []
            for world in worlds:
                a, b = lookup.get((seed, world, *first)), lookup.get((seed, world, *second))
                if a is None or b is None or a["status"] != "valid" or b["status"] != "valid":
                    return dict(complete=False, mean_difference=None,
                                reason="Missing or failed paired outcomes; no imputation")
                line.append(value(a) - value(b))
            matrix.append(line)
        return dict(complete=True, mean_difference=float(np.mean(matrix)),
            exploratory_crossed_bootstrap_95_interval=crossed_interval(matrix),
            per_training_seed_mean_difference=[float(np.mean(x)) for x in matrix])

    result = {}
    for demand in DEMANDS:
        means, differences = {}, {}
        for policy, communication in SLOTS:
            own = [lookup.get((s, w, demand, policy, communication)) for s in seeds for w in worlds]
            retained = [r for r in own if r is not None]
            valid = [r for r in retained if r["status"] == "valid"]
            entry = dict(planned=planned, retained=len(retained), valid=len(valid),
                failed=len(retained) - len(valid), missing=planned - len(retained),
                mean_products_valid_only=float(np.mean([r["produced"] for r in valid])) if valid else None,
                per_training_seed_mean_products={str(s): float(np.mean([
                    r["produced"] for r in valid if r["training_seed"] == s]))
                    if any(r["training_seed"] == s for r in valid) else None for s in seeds})
            entry["mean_counts_valid_only"] = {
                name: float(np.mean([r[name] for r in valid])) for name in (
                    "attempts", "delivered", "forwarded", "cross_site_deliveries",
                    "read_report_inputs", "travel_ticks", "work_ticks", "empty_trips", "loaded_trips",
                    "empty_trips_with_report_delivery", "loaded_trips_with_report_delivery",
                    "empty_travel_ticks", "loaded_travel_ticks", "demand_issued", "demand_expired",
                    "demand_pending", "demand_reserved", "late_completed", "work_denials",
                    "pickup_denials", "drop_denials", "drops_without_current_need")
                if valid and all(name in r for r in valid)}
            if valid and all("phase_counts" in r for r in valid):
                entry["mean_phase_counts_valid_only"] = {
                    phase: {name: float(np.mean([r["phase_counts"][phase][name] for r in valid]))
                            for name in valid[0]["phase_counts"][phase]}
                    for phase in ("early", "late", "quiet")}
            if valid and all("activity_by_half" in r for r in valid):
                entry["mean_activity_by_half_valid_only"] = [dict(
                    produced=float(np.mean([r["activity_by_half"][h]["produced"] for r in valid])),
                    personal_cost=float(np.mean([r["activity_by_half"][h]["personal_cost"] for r in valid])),
                    action_counts={a: float(np.mean([
                        r["activity_by_half"][h]["action_counts"][a] for r in valid])) for a in ACTIONS})
                    for h in range(2)]
            means[f"{policy}:{communication}"] = entry
            if (policy, communication) != ("trained", "local"):
                differences[f"trained_local_minus_{policy}:{communication}"] = paired(
                    (demand, "trained", "local"), (demand, policy, communication))
        for communication in ("no_messages", "unread", "instant"):
            differences[f"scripted_local_minus_scripted:{communication}"] = paired(
                (demand, "scripted_local", "local"), (demand, "scripted_local", communication))
        result[demand] = dict(conditions=means, paired_production_differences=differences)
    result["shutdown_minus_recurring_trained_local"] = dict(
        second_half_production=paired(("shutdown", "trained", "local"),
            ("recurring", "trained", "local"), lambda r: r["activity_by_half"][1]["produced"]),
        second_half_share_decisions=paired(("shutdown", "trained", "local"),
            ("recurring", "trained", "local"), lambda r: r["activity_by_half"][1]["action_counts"]["SHARE"]),
        second_half_travel_decisions=paired(("shutdown", "trained", "local"),
            ("recurring", "trained", "local"), lambda r: sum(n for a, n in
                r["activity_by_half"][1]["action_counts"].items() if a.startswith("GO_"))),
        quiet_window_travel_ticks=paired(("shutdown", "trained", "local"),
            ("recurring", "trained", "local"), lambda r: r["phase_counts"]["quiet"]["travel_ticks"]),
        quiet_window_share_attempts=paired(("shutdown", "trained", "local"),
            ("recurring", "trained", "local"), lambda r: r["phase_counts"]["quiet"]["attempts"]),
        interpretation="Changed workload and policy response together; not proof of a profession or service benefit")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=240)
    parser.add_argument("--training-seeds", default="17,23,41")
    parser.add_argument("--worlds", type=int, default=12)
    parser.add_argument("--evaluation-seed-start", type=int, default=9500000)
    parser.add_argument("--agents", type=int, default=4)
    parser.add_argument("--horizon", type=int, default=160)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        seeds = [int(value) for value in args.training_seeds.split(",")]
    except ValueError:
        parser.error("Training seeds must be integers")
    if (not 1 <= len(seeds) <= 3 or len(set(seeds)) != len(seeds) or min(seeds) < 0
            or min(args.episodes, args.worlds, args.agents, args.horizon) < 1
            or args.evaluation_seed_start < 0):
        parser.error("Use positive dimensions and one to three distinct nonnegative training seeds")
    worlds = list(range(args.evaluation_seed_start, args.evaluation_seed_start + args.worlds))
    training_worlds = {stable_seed("demand-training-world", s, e)
                       for s in seeds for e in range(args.episodes)}
    if training_worlds.intersection(worlds):
        raise ValueError("Training/evaluation world seed collision")
    destination = args.output_dir
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Output directory is nonempty; preserve prior runs")
    destination.mkdir(parents=True, exist_ok=True)
    protocol = dict(schema=SCHEMA, origin="ABSTRACT_SIMULATOR_ONLY", pilot_only=True,
        training_seeds=seeds, episodes_per_training_seed=args.episodes,
        heldout_world_seeds=worlds, agents=args.agents, horizon_ticks=args.horizon,
        gamma_per_tick=GAMMA, personal_reward_weight=PERSONAL_WEIGHT,
        training_communication="local", training_demand_schedule="alternate recurring, shutdown by episode",
        evaluation_demand=list(DEMANDS), evaluation_slots=[list(s) for s in SLOTS],
        observation_contract=observation_contract(), training_settings=SETTINGS,
        numpy_version=np.__version__, primary_metric="completed simulated work-order units",
        primary_comparison="recurring: frozen trained local minus same initialization untrained local",
        information_comparison="recurring: frozen trained local minus frozen trained unread",
        mechanism_comparison="same observation-only heuristic local versus unread/no-messages",
        planned_evaluation_slots=len(seeds) * len(worlds) * len(DEMANDS) * len(SLOTS),
        independent_units="crossed training seed and world seed; citizens and ticks are not replicates",
        repeated_script_and_random_rows_are_not_independent_replications=True,
        roles_are_observational=True, learned_specialization_established=False,
        delivery_reward=0, occupation_reward=0, recurrent_network=False,
        centralized_critic=False, forge_control_enabled=False, minecraft_worlds=0,
        confirmatory_study=False, uncertainty="exploratory crossed bootstrap; few training seeds")
    protocol_bytes = (json.dumps(protocol, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    (destination / "protocol.json").write_bytes(protocol_bytes)
    rows, training = [], []
    progress = lambda entry: print(json.dumps(entry, allow_nan=False), flush=True)
    for seed in seeds:
        model, initial, statistics = train(seed, args.episodes, agents=args.agents,
                                          horizon=args.horizon, progress=progress)
        if source_manifest() != protocol["observation_contract"]["source_manifest"]:
            raise AssertionError("Environment or learner source changed during the declared experiment")
        if not model.updates or model.digest() == initial.digest():
            raise AssertionError("No neural parameter learning occurred")
        trained_path, initial_path = destination / f"trained-{seed}.json", destination / f"untrained-{seed}.json"
        model.save(trained_path)
        initial.save(initial_path)
        training.append(dict(training_seed=seed, trained_sha256=model.digest(),
                             initial_sha256=initial.digest(), **statistics))
        model, initial = Network.load(trained_path), Network.load(initial_path)
        results, examples = evaluate(model, initial, worlds, agents=args.agents,
                                     horizon=args.horizon, evaluation_scope=str(seed))
        results = [dict(training_seed=seed, **row) for row in results]
        rows.extend(results)
        with (destination / "outcomes.jsonl").open("a") as stream:
            for row in results:
                stream.write(json.dumps(row, allow_nan=False) + "\n")
        (destination / f"examples-{seed}.json").write_text(json.dumps(examples, allow_nan=False) + "\n")
        (destination / "training.json").write_text(json.dumps(training, indent=2, allow_nan=False) + "\n")
        progress(dict(training_seed=seed, stage="evaluated", valid=sum(r["status"] == "valid" for r in results),
                      planned=len(worlds) * len(DEMANDS) * len(SLOTS), **statistics))
    report = dict(protocol=protocol, protocol_sha256=hashlib.sha256(protocol_bytes).hexdigest(),
        training=training, evaluation_weights_frozen=True, summary=summarize(rows, seeds, worlds),
        runs=rows, learned_specialization_established=False, forge_control_enabled=False,
        minecraft_worlds=0, confirmatory_study=False)
    (destination / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    progress(dict(report=str(destination / "report.json"), summary=report["summary"]))


if __name__ == "__main__":
    main()

