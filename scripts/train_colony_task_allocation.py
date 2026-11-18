#!/usr/bin/env python3
"""Reward-trained shared DQN for bounded task allocation. ABSTRACT SIMULATOR ONLY."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import random

import numpy as np

from colony_task_env import (Env, FEATURES, ACTIONS, HUB_SCALE, SCHEMA as OBSERVATION_SCHEMA,
                             mask, scripted_balance, scripted_nearest)

SCHEMA = "hearthbound.simulated-colony-allocation.v0.4"
GAMMA = 0.98  # Per simulation tick, never per option.
PERSONAL_WEIGHT = 0.25
REGIMES = ("standard", "long_routes", "scarce_b")
TRAINING_SETTINGS = {"hidden_units": 64, "batch_size": 32, "replay_start": 64,
    "replay_capacity": 20000, "replay_trim": 2000, "target_update_interval": 200,
    "adam_rate": 0.001, "epsilon_initial": 0.9, "epsilon_final": 0.08,
    "epsilon_decay_fraction": 0.8, "updates_per_world_tick": 1,
    "algorithm": "shared-independent-Double-DQN", "gradient_norm_clip": 5.0,
    "loss": "Huber with delta 1"}


def source_manifest():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ("colony_task_env.py", "train_colony_task_allocation.py")}


def observation_contract():
    return {"schema": OBSERVATION_SCHEMA, "features": list(FEATURES), "actions": list(ACTIONS),
            "hub_scale": HUB_SCALE, "source_scale": 4, "travel_scale": 24,
            "age_scale": "episode horizon", "pending_scale": "public agent count",
            "source_manifest": source_manifest()}


def stable_seed(*parts):
    return int.from_bytes(hashlib.sha256(repr(parts).encode()).digest()[:8], "big")


class Network:
    def __init__(self, seed, hidden=64):
        rng = np.random.default_rng(seed)
        self.parameters = {
            "w1": rng.normal(0, math.sqrt(2 / len(FEATURES)), (len(FEATURES), hidden)),
            "b1": np.zeros(hidden),
            "w2": rng.normal(0, 0.03, (hidden, len(ACTIONS))),
            "b2": np.zeros(len(ACTIONS)),
        }
        self.m = {k: np.zeros_like(v) for k, v in self.parameters.items()}
        self.v = {k: np.zeros_like(v) for k, v in self.parameters.items()}
        self.updates = 0

    def values(self, x):
        p = self.parameters
        return np.maximum(np.asarray(x) @ p["w1"] + p["b1"], 0) @ p["w2"] + p["b2"]

    def greedy(self, observation):
        return int(np.argmax(np.where(mask(observation), self.values(observation), -np.inf)))

    def digest(self):
        h = hashlib.sha256()
        for name, value in sorted(self.parameters.items()):
            h.update(name.encode())
            h.update(repr(value.shape).encode())
            h.update(value.astype("<f8").tobytes())
        return h.hexdigest()

    def update(self, batch, target, rate=0.001):
        x = np.asarray([t["observation"] for t in batch])
        nx = np.asarray([t["next_observation"] for t in batch])
        actions = np.asarray([t["action"] for t in batch])
        rewards = np.asarray([t["discounted_reward"] for t in batch])
        discounts = np.asarray([GAMMA ** t["duration"] for t in batch])
        terminal = np.asarray([t["terminal"] for t in batch])
        masks = np.asarray([mask(row) for row in nx])
        choices = np.argmax(np.where(masks, self.values(nx), -np.inf), axis=1)
        future = target.values(nx)[np.arange(len(batch)), choices]
        expected = rewards + discounts * (~terminal) * future
        p = self.parameters
        z = x @ p["w1"] + p["b1"]
        hidden = np.maximum(z, 0)
        q = hidden @ p["w2"] + p["b2"]
        errors = q[np.arange(len(batch)), actions] - expected
        if not np.isfinite(errors).all():
            raise ValueError("Nonfinite training transition")
        dq = np.zeros_like(q)
        dq[np.arange(len(batch)), actions] = np.clip(errors, -1, 1) / len(batch)
        dh = (dq @ p["w2"].T) * (z > 0)
        gradients = {"w2": hidden.T @ dq, "b2": dq.sum(axis=0),
                     "w1": x.T @ dh, "b1": dh.sum(axis=0)}
        norm = math.sqrt(sum(float(np.sum(g*g)) for g in gradients.values()))
        self.updates += 1
        for name, gradient in gradients.items():
            gradient *= min(1.0, 5.0 / max(norm, 1e-12))
            self.m[name] = 0.9 * self.m[name] + 0.1 * gradient
            self.v[name] = 0.999 * self.v[name] + 0.001 * gradient * gradient
            m = self.m[name] / (1 - 0.9 ** self.updates)
            v = self.v[name] / (1 - 0.999 ** self.updates)
            p[name] -= rate * m / (np.sqrt(v) + 1e-8)

    def save(self, destination):
        data = {"schema": SCHEMA, "features": FEATURES, "actions": ACTIONS,
                "observation_contract": observation_contract(),
                "parameter_sha256": self.digest(),
                "parameters": {k: v.tolist() for k, v in self.parameters.items()}}
        destination.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n")

    @classmethod
    def load(cls, source):
        data = json.loads(source.read_text())
        if (data.get("schema") != SCHEMA or data.get("features") != list(FEATURES)
                or data.get("actions") != list(ACTIONS)
                or data.get("observation_contract") != observation_contract()):
            raise ValueError("Checkpoint observation/action schema mismatch")
        parameters = {k: np.asarray(v, dtype=float) for k, v in data["parameters"].items()}
        if set(parameters) != {"w1", "b1", "w2", "b2"}:
            raise ValueError("Checkpoint parameter keys mismatch")
        hidden = parameters["b1"].size
        expected = {"w1": (len(FEATURES), hidden), "b1": (hidden,),
                    "w2": (hidden, len(ACTIONS)), "b2": (len(ACTIONS),)}
        if not 1 <= hidden <= 256 or any(parameters[k].shape != shape
                or not np.isfinite(parameters[k]).all() for k, shape in expected.items()):
            raise ValueError("Invalid checkpoint tensor")
        model = cls(0, hidden=hidden)
        model.parameters = parameters
        if model.digest() != data.get("parameter_sha256"):
            raise ValueError("Checkpoint parameter digest mismatch")
        return model


def run_episode(policy, world, *, on_transition=None, on_tick=None, trace=False):
    """Accumulate each actor's exact tick rewards until its next decision or episode end."""
    pending = {}
    transitions = []
    action_trace = []
    personal_totals = [0.0] * world.agents
    colony_total = 0.0

    def complete(agent, terminal):
        item = pending.pop(agent)
        if item["duration"] < 1:
            raise AssertionError("Zero-duration policy transition")
        item["next_observation"] = tuple(world.obs(agent))
        item["terminal"] = terminal
        transitions.append(item)
        if on_transition:
            on_transition(item)

    while not world.done:
        ready = world.ready()
        actions = {}
        observations = {agent: tuple(world.obs(agent)) for agent in ready}
        for agent in ready:
            if agent in pending:
                complete(agent, False)
            observation = observations[agent]
            action = int(policy(agent, observation))
            if not mask(observation)[action]:
                raise AssertionError("Policy violated local action mask")
            actions[agent] = action
            pending[agent] = {"agent": agent, "start_tick": world.tick,
                "observation": observation, "action": action, "duration": 0,
                "discounted_reward": 0.0, "personal_reward": 0.0, "colony_reward": 0.0}
            if trace:
                action_trace.append({"tick": world.tick, "agent": agent,
                                     "action": ACTIONS[action], "observation": observation})
        colony, personal, done = world.step(actions)
        if not math.isfinite(colony) or not all(math.isfinite(r) for r in personal):
            raise AssertionError("Invalid environment reward")
        colony_total += colony
        for agent, item in pending.items():
            scalar = colony + PERSONAL_WEIGHT * personal[agent]
            item["discounted_reward"] += GAMMA ** item["duration"] * scalar
            item["duration"] += 1
            item["personal_reward"] += personal[agent]
            item["colony_reward"] += colony
            personal_totals[agent] += personal[agent]
        if done:
            for agent in list(pending):
                complete(agent, True)
        if on_tick:
            on_tick()
    # Every agent has one continuous experience ledger over the entire horizon.
    for agent in range(len(personal_totals)):
        own = [t for t in transitions if t["agent"] == agent]
        if sum(t["duration"] for t in own) != world.horizon:
            raise AssertionError("Missing/overlapping agent time")
        if [t["start_tick"] for t in own] != list(np.cumsum([0] + [t["duration"] for t in own[:-1]])):
            raise AssertionError("Noncontiguous agent experience")
    metrics = world.metrics()
    if metrics["produced"] != colony_total:
        raise AssertionError("Production reward does not match actual simulated output")
    if any(metrics[k] != 0 for k in ("conservation_residual_A", "conservation_residual_B")):
        raise AssertionError("Resource accounting failed")
    metrics.update(personal_reward=personal_totals, colony_reward=colony_total,
                   policy_decisions=len(transitions))
    if trace:
        metrics["action_trace"] = action_trace
        metrics["world_events"] = copy.deepcopy(world.events)
    return metrics, transitions


def train(seed, episodes, *, agents=2, horizon=64):
    online = Network(seed)
    initial = copy.deepcopy(online)
    target = copy.deepcopy(online)
    rng = random.Random(stable_seed("policy-exploration", seed))
    replay = []
    decisions = 0
    training_products = 0
    world_digest = hashlib.sha256()
    for episode in range(episodes):
        world_seed = stable_seed("training-world", seed, episode)
        world_digest.update(str(world_seed).encode())
        world = Env(world_seed, agents=agents, horizon=horizon, regime="standard")
        epsilon = 0.08 + 0.82 * max(0, 1 - episode / max(1, episodes * 0.8))

        def policy(agent, obs):
            valid = [i for i, ok in enumerate(mask(obs)) if ok]
            return rng.choice(valid) if rng.random() < epsilon else online.greedy(obs)

        def remember(transition):
            replay.append(transition)
            if len(replay) > TRAINING_SETTINGS["replay_capacity"]:
                del replay[:TRAINING_SETTINGS["replay_trim"]]

        def learn():
            if len(replay) < TRAINING_SETTINGS["replay_start"]:
                return
            online.update(rng.sample(replay, TRAINING_SETTINGS["batch_size"]), target,
                          rate=TRAINING_SETTINGS["adam_rate"])
            if online.updates % TRAINING_SETTINGS["target_update_interval"] == 0:
                target.parameters = {k: v.copy() for k, v in online.parameters.items()}

        metrics, transitions = run_episode(policy, world, on_transition=remember, on_tick=learn)
        decisions += len(transitions)
        training_products += metrics["produced"]
    return online, initial, {"episodes": episodes, "world_ticks": episodes * horizon,
        "agent_ticks": episodes * horizon * agents, "decisions": decisions,
        "optimizer_updates": online.updates, "training_products": training_products,
        "training_world_seed_manifest_sha256": world_digest.hexdigest()}


def evaluate(model, initial, world_seeds, regime, *, agents=2, horizon=64):
    before = (model.digest(), initial.digest(), model.updates, initial.updates)
    rows, examples = [], {}
    for index, seed in enumerate(world_seeds):
        for name in ("trained", "untrained", "scripted_balance", "scripted_nearest", "random"):
            rng = random.Random(stable_seed("evaluation-random-policy", seed, regime))
            if name == "trained":
                policy = lambda agent, obs: model.greedy(obs)
            elif name == "untrained":
                policy = lambda agent, obs: initial.greedy(obs)
            elif name == "scripted_balance":
                policy = lambda agent, obs: scripted_balance(obs, agents=agents)
            elif name == "scripted_nearest":
                policy = lambda agent, obs: scripted_nearest(obs)
            else:
                policy = lambda agent, obs: rng.choice([i for i, ok in enumerate(mask(obs)) if ok])
            result, _ = run_episode(policy, Env(seed, agents=agents, horizon=horizon, regime=regime),
                                    trace=index == 0)
            if index == 0:
                examples[name] = {"world_seed": seed, "action_trace": result.pop("action_trace"),
                                  "world_events": result.pop("world_events")}
            rows.append({"world_seed": seed, "regime": regime, "policy": name, **result})
    if before != (model.digest(), initial.digest(), model.updates, initial.updates):
        raise AssertionError("Evaluation mutated a frozen checkpoint")
    return rows, examples


def crossed_interval(matrix, seed=5404, repeats=2000):
    """Crossed resampling of independent training seeds and paired world seeds."""
    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2 or not np.isfinite(values).all() or min(values.shape) < 1:
        raise ValueError("Invalid paired-run matrix")
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(repeats):
        train = rng.integers(values.shape[0], size=values.shape[0])
        worlds = rng.integers(values.shape[1], size=values.shape[1])
        means.append(float(values[np.ix_(train, worlds)].mean()))
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def summarize(rows, training_seeds, world_seeds):
    report = {}
    lookup = {(r["training_seed"], r["world_seed"], r["regime"], r["policy"]): r for r in rows}
    for regime in sorted({r["regime"] for r in rows}):
        summary = {}
        for name in ("trained", "untrained", "scripted_balance", "scripted_nearest", "random"):
            own = [r for r in rows if r["regime"] == regime and r["policy"] == name]
            summary[name] = {"mean_products": float(np.mean([r["produced"] for r in own])),
                "mean_denials": float(np.mean([r["denials"] for r in own])),
                "mean_delivered": float(np.mean([r["deliveredA"] + r["deliveredB"] for r in own])),
                "conservation_violations": sum(r["conservation_residual_A"] != 0
                    or r["conservation_residual_B"] != 0 for r in own)}
        for comparator in ("untrained", "scripted_balance", "scripted_nearest", "random"):
            matrix = [[lookup[(t, w, regime, "trained")]["produced"]
                       - lookup[(t, w, regime, comparator)]["produced"] for w in world_seeds]
                      for t in training_seeds]
            low, high = crossed_interval(matrix)
            delta = float(np.mean(matrix))
            summary["trained_minus_" + comparator] = {
                "mean_products_difference": delta,
                "crossed_bootstrap_95_percent_interval": [low, high],
                "per_training_seed_mean_difference": [float(np.mean(x)) for x in matrix],
                "pilot_criterion_met": delta >= 0.25 and low > 0}
        report[regime] = summary
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--episodes", type=int, default=600)
    p.add_argument("--training-seeds", default="17,23,41")
    p.add_argument("--worlds", type=int, default=40)
    p.add_argument("--evaluation-seed-start", type=int, default=9000000)
    p.add_argument("--agents", type=int, default=2)
    p.add_argument("--horizon", type=int, default=64)
    p.add_argument("--regimes", default=",".join(REGIMES))
    p.add_argument("--output-dir", type=Path, default=Path("run/colony-allocation-v0-4"))
    args = p.parse_args()
    seeds = [int(x) for x in args.training_seeds.split(",")]
    regimes = args.regimes.split(",")
    if (args.episodes < 1 or args.worlds < 1 or not seeds or len(set(seeds)) != len(seeds)
            or any(s < 0 for s in seeds)):
        p.error("Positive episode/world counts and distinct training seeds required")
    if not regimes or len(set(regimes)) != len(regimes) or any(x not in REGIMES for x in regimes):
        p.error("Invalid evaluation regimes")
    world_seeds = [args.evaluation_seed_start + i for i in range(args.worlds)]
    # Training uses independently hashed seeds; enforce disjointness explicitly.
    training_worlds = {stable_seed("training-world", s, i) for s in seeds for i in range(args.episodes)}
    if training_worlds.intersection(world_seeds):
        raise AssertionError("Training/evaluation world seed collision")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError("Output directory is not empty; choose a new run directory")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    protocol = {"schema": SCHEMA, "episodes_per_training_seed": args.episodes,
        "training_seeds": seeds, "heldout_world_seeds": world_seeds,
        "regimes": regimes, "agents": args.agents, "horizon_ticks": args.horizon,
        "gamma_per_tick": GAMMA, "personal_reward_weight": PERSONAL_WEIGHT,
        "feature_names": FEATURES, "actions": ACTIONS,
        "observation_contract": observation_contract(), "training_settings": TRAINING_SETTINGS,
        "numpy_version": np.__version__,
        "primary_metric": "completed production batches by fixed horizon",
        "primary_regime": "standard", "pilot_only": True,
        "pilot_learning_criterion": "trained-minus-untrained mean products >=0.25, interval lower bound >0",
        "scripted_superiority_is_separate": True,
        "communication_benefit_tested": False, "minecraft_transfer_tested": False}
    protocol_bytes = (json.dumps(protocol, sort_keys=True, indent=2) + "\n").encode()
    protocol_path = args.output_dir / "protocol.json"
    protocol_path.write_bytes(protocol_bytes)
    rows, runs = [], []
    for seed in seeds:
        model, initial, stats = train(seed, args.episodes, agents=args.agents, horizon=args.horizon)
        if model.digest() == initial.digest() or model.updates < 1:
            raise AssertionError("No actual neural parameter learning occurred")
        model.save(args.output_dir / f"trained-{seed}.json")
        initial.save(args.output_dir / f"untrained-{seed}.json")
        runs.append({"training_seed": seed, **stats, "trained_sha256": model.digest(),
                     "untrained_sha256": initial.digest()})
        # Evaluate deserialized, frozen weights rather than live optimizer state.
        model = Network.load(args.output_dir / f"trained-{seed}.json")
        initial = Network.load(args.output_dir / f"untrained-{seed}.json")
        for regime in regimes:
            result, examples = evaluate(model, initial, world_seeds, regime,
                                        agents=args.agents, horizon=args.horizon)
            rows.extend({"training_seed": seed, **r} for r in result)
            (args.output_dir / f"examples-{seed}-{regime}.json").write_text(
                json.dumps(examples, separators=(",", ":"), allow_nan=False) + "\n")
        print(json.dumps({"seed": seed, "optimizer_updates": stats["optimizer_updates"],
                          "training_products": stats["training_products"]}), flush=True)
    report = {"schema": SCHEMA, "origin": "ABSTRACT_SIMULATOR_ONLY", "numpy_version": np.__version__,
        "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "agents": args.agents, "horizon_ticks": args.horizon, "features": FEATURES, "actions": ACTIONS,
        "gamma_per_tick": GAMMA, "personal_reward_weight": PERSONAL_WEIGHT,
        "training_seeds": seeds, "heldout_world_seeds": world_seeds, "training_runs": runs,
        "evaluation_weights_frozen": True, "forge_control_enabled": False,
        "communication_benefit_tested": False, "learned_roles_tested": False,
        "confirmatory_study": False, "primary_regime": "standard",
        "predeclared_pilot_criterion": "mean product gain >=0.25 with crossed-bootstrap lower bound >0",
        "independent_units": "crossed training seed and world seed; agents/ticks are not replicates",
        "summary": summarize(rows, seeds, world_seeds), "runs": rows}
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"report": str(args.output_dir / "report.json"), "summary": report["summary"]}), flush=True)


if __name__ == "__main__":
    main()
