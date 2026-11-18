#!/usr/bin/env python3
"""Matched action-alias and fixed-replay diagnostics. ABSTRACT SIMULATOR ONLY."""
import argparse
from collections import Counter
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import random

import numpy as np

import train_colony_task_allocation as base
from colony_task_env import Env, ACTIONS, mask, scripted_balance, scripted_nearest
from colony_allocation_alias import decision_mask, choose, is_current_inspection

SCHEMA = "hearthbound.colony-allocation-diagnostics.v0.5"
GAMMA = base.GAMMA
LEGACY_DIGESTS = {
    17: "4003ec32f02502a526653c71f14e8ae14ab5ea7fca6bc0fca1bd1c2363a363b8",
    23: "a7ce709660284e6f410fc90b4c0e7e622f0b474e4bd81a58eb06f66d0f159625",
    41: "f9fa58b95d76d47f1271920523f8e44d299f5838d5da57cabfece2de692e6295",
}
ORIGINAL_SOURCES = {
    "colony_task_env.py": "4ee01ecd931a41f1a247502109ffc398280bcf2ae4c2b82c3188d48349e0c1ad",
    "train_colony_task_allocation.py": "4ba409ae3521dbbc2bf7018b2aa4afc9774495a8b19fe3d63119992797817588",
}


def sources():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in (*ORIGINAL_SOURCES, "colony_allocation_alias.py",
                         "colony_allocation_diagnostics.py")}


def canonical_record(record):
    return (json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def validate_link(records, index, successor):
    if type(successor) is not int or not 0 <= successor < len(records):
        raise ValueError("Invalid replay successor")
    current, nxt = records[index], records[successor]
    if (current["terminal"] or current["agent"] != nxt["agent"]
            or current["episode"] != nxt["episode"]
            or current["start_tick"] + current["duration"] != nxt["start_tick"]
            or tuple(current["next_observation"]) != tuple(nxt["observation"])):
        raise ValueError("Replay window crosses an agent, episode, or time boundary")
    return nxt


def greedy_backup(records, start, online, max_options):
    """Extend only through recorded greedy successor actions; cut before off-policy reward.

    This is a finite greediness-truncated return, not an implementation of
    Retrace(lambda) or a convergence guarantee for partially observed neural MARL.
    Both training arms retain the full original action mask.
    """
    if type(start) is not int or not 0 <= start < len(records):
        raise ValueError("Invalid replay index")
    if type(max_options) is not int or max_options < 1:
        raise ValueError("Invalid backup length")
    first = records[start]
    result = dict(first)
    reward, duration = first["discounted_reward"], first["duration"]
    if (type(duration) is not int or duration < 1 or not math.isfinite(reward)
            or type(first["terminal"]) is not bool):
        raise ValueError("Invalid replay transition")
    current, index, depth = first, start, 1
    reason = "depth_limit"
    while depth < max_options and not current["terminal"]:
        successor = current["next_index"]
        nxt = validate_link(records, index, successor)
        if nxt["action"] != online.greedy(nxt["observation"]):
            reason = "non_greedy_successor"
            break
        if (type(nxt["duration"]) is not int or nxt["duration"] < 1
                or not math.isfinite(nxt["discounted_reward"])):
            raise ValueError("Invalid successor reward or duration")
        reward += GAMMA ** duration * nxt["discounted_reward"]
        duration += nxt["duration"]
        current, index, depth = nxt, successor, depth + 1
    if current["terminal"]:
        reason = "terminal"
    result.update(discounted_reward=reward, duration=duration,
                  next_observation=current["next_observation"], terminal=current["terminal"],
                  backup_depth=depth, cut_reason=reason)
    return result


def collect_corpus(seed, episodes, horizon=64, agents=2):
    if type(episodes) is not int or episodes < 1:
        raise ValueError("Positive corpus episode count required")
    records, products, seed_hash = [], 0, hashlib.sha256()
    for episode in range(episodes):
        world_seed = base.stable_seed("diagnostic-training-world", seed, episode)
        seed_hash.update(str(world_seed).encode())
        rng = random.Random(base.stable_seed("diagnostic-random-behavior", seed, episode))
        def behavior(agent, observation):
            return rng.choice([a for a, valid in enumerate(mask(observation)) if valid])
        metrics, transitions = base.run_episode(behavior,
            Env(world_seed, agents=agents, horizon=horizon, regime="standard"))
        if (metrics["conservation_residual_A"] != 0 or metrics["conservation_residual_B"] != 0
                or metrics["tick"] != horizon):
            raise AssertionError("Behavior corpus violates physical/time accounting")
        products += metrics["produced"]
        offset = len(records)
        for item in transitions:
            records.append(dict(item, episode=episode, world_seed=world_seed, next_index=None))
        for agent in range(agents):
            indices = [offset + i for i, t in enumerate(transitions) if t["agent"] == agent]
            for current, nxt in zip(indices, indices[1:]):
                records[current]["next_index"] = nxt
                validate_link(records, current, nxt)
            if not indices or not records[indices[-1]]["terminal"]:
                raise AssertionError("Incomplete behavior episode")
    digest = hashlib.sha256()
    for record in records:
        digest.update(canonical_record(record))
    return records, {"behavior": "UNIFORM_RANDOM_OVER_FULL_LOCAL_MASK",
        "episodes": episodes, "world_ticks": episodes * horizon,
        "agent_ticks": episodes * horizon * agents, "transitions": len(records),
        "corpus_products": products, "corpus_sha256": digest.hexdigest(),
        "world_seed_manifest_sha256": seed_hash.hexdigest()}


def train_fixed(seed, records, updates):
    if type(updates) is not int or updates < 1 or len(records) < 32:
        raise ValueError("Insufficient matched replay or optimizer budget")
    initial = base.Network(seed)
    models = {"offline_td": copy.deepcopy(initial), "offline_greedy5": copy.deepcopy(initial)}
    targets = {name: copy.deepcopy(model) for name, model in models.items()}
    depths = {name: Counter() for name in models}
    reasons = {name: Counter() for name in models}
    durations = Counter()
    rng = random.Random(base.stable_seed("diagnostic-minibatches", seed))
    sampled_hash = hashlib.sha256()
    for update in range(updates):
        starts = rng.sample(range(len(records)), 32)
        sampled_hash.update((",".join(map(str, starts)) + "\n").encode())
        # The same starting indices, initialization, gradient budget and target
        # copy schedule are used. Additional successor rewards are the intervention.
        for name, model in models.items():
            batch = [greedy_backup(records, i, model, 1 if name == "offline_td" else 5)
                     for i in starts]
            depths[name].update(t["backup_depth"] for t in batch)
            reasons[name].update(t["cut_reason"] for t in batch)
            durations[name] += sum(t["duration"] for t in batch)
            model.update(batch, targets[name], rate=0.001)
            if (update + 1) % 200 == 0:
                targets[name].parameters = {k: v.copy() for k, v in model.parameters.items()}
    stats = {}
    for name, model in models.items():
        samples = sum(depths[name].values())
        stats[name] = {"optimizer_updates": model.updates, "sampled_starts": samples,
            "sampled_start_order_sha256": sampled_hash.hexdigest(),
            "initial_parameter_sha256": initial.digest(), "parameter_sha256": model.digest(),
            "backup_depth_histogram": dict(depths[name]), "cut_reasons": dict(reasons[name]),
            "mean_backup_options": sum(k * v for k, v in depths[name].items()) / samples,
            "fraction_multistep": 1 - depths[name][1] / samples,
            "mean_backup_ticks": durations[name] / samples}
    return models, initial, stats


def save_reload(model, path, protocol_hash, label):
    model.save(path)
    data = json.loads(path.read_text())
    data["diagnostic_contract"] = {"schema": SCHEMA, "protocol_sha256": protocol_hash,
                                   "label": label, "source_manifest": sources()}
    path.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n")
    saved = json.loads(path.read_text())
    if saved["diagnostic_contract"]["source_manifest"] != sources():
        raise AssertionError("Diagnostic source changed during checkpoint creation")
    reloaded = base.Network.load(path)
    if reloaded.digest() != model.digest():
        raise AssertionError("Checkpoint failed exact parameter roundtrip")
    return reloaded


def evaluate(models, world_seeds, regimes, agents=2, horizon=64):
    before = {name: (model.digest(), model.updates) for name, model in models.items()}
    rows, examples = [], {}
    for regime in regimes:
        for world_index, world_seed in enumerate(world_seeds):
            for name in (*models, "scripted_balance", "scripted_nearest", "random"):
                for prune in (False, True):
                    counters = Counter()
                    rng = random.Random(base.stable_seed("diagnostic-eval-random", world_seed, regime))
                    def policy(agent, observation):
                        allowed = decision_mask(observation, prune)
                        if name in models:
                            action = choose(models[name], observation, prune)
                        elif name == "scripted_balance":
                            action = scripted_balance(observation, agents=agents)
                        elif name == "scripted_nearest":
                            action = scripted_nearest(observation)
                        else:
                            action = rng.choice([i for i, ok in enumerate(allowed) if ok])
                        if not allowed[action]:
                            raise AssertionError("Policy selected an unavailable diagnostic action")
                        counters["same_site_inspections"] += int(is_current_inspection(observation, action))
                        counters["wait_decisions"] += int(action == 0)
                        counters["wait_with_haul_available"] += int(action == 0 and any(mask(observation)[5:]))
                        return action
                    result, _ = base.run_episode(policy,
                        Env(world_seed, agents=agents, horizon=horizon, regime=regime),
                        trace=world_index == 0)
                    if (result["conservation_residual_A"] != 0 or result["conservation_residual_B"] != 0
                            or result["tick"] != horizon
                            or (prune and counters["same_site_inspections"] != 0)):
                        raise AssertionError("Evaluation violates physical/time/mask accounting")
                    if world_index == 0:
                        examples[f"{regime}:{name}:{'pruned' if prune else 'full'}"] = {
                            "world_seed": world_seed, "action_trace": result.pop("action_trace"),
                            "world_events": result.pop("world_events")}
                    rows.append(dict(world_seed=world_seed, regime=regime, policy=name,
                                     pruned=prune, **result, **counters))
    if before != {name: (model.digest(), model.updates) for name, model in models.items()}:
        raise AssertionError("Evaluation changed frozen weights or optimizer state")
    return rows, examples


def summarize(rows, seeds, worlds):
    lookup = {(r["training_seed"], r["world_seed"], r["regime"], r["policy"], r["pruned"]): r
              for r in rows}
    result = {}
    for regime in sorted({r["regime"] for r in rows}):
        means = {}
        for policy in sorted({r["policy"] for r in rows}):
            for prune in (False, True):
                own = [r for r in rows if r["regime"] == regime
                       and r["policy"] == policy and r["pruned"] == prune]
                means[f"{policy}:{'pruned' if prune else 'full'}"] = {
                    "products": float(np.mean([r["produced"] for r in own])),
                    "same_site_inspections": float(np.mean([r["same_site_inspections"] for r in own])),
                    "wait_decisions": float(np.mean([r["wait_decisions"] for r in own])),
                    "travel_ticks": float(np.mean([r["totaltravel"] for r in own])),
                    "denials": float(np.mean([r["denials"] for r in own]))}
        comparisons = [
            ("credit_full", ("offline_greedy5", False), ("offline_td", False)),
            ("credit_pruned_secondary", ("offline_greedy5", True), ("offline_td", True)),
            ("alias_offline_td", ("offline_td", True), ("offline_td", False)),
            ("alias_offline_greedy5", ("offline_greedy5", True), ("offline_greedy5", False)),
            ("alias_random", ("random", True), ("random", False)),
        ]
        if "legacy_online" in {r["policy"] for r in rows}:
            comparisons.insert(0, ("alias_legacy_primary", ("legacy_online", True), ("legacy_online", False)))
        effects = {}
        for label, positive, negative in comparisons:
            matrix = [[lookup[(seed, world, regime, *positive)]["produced"]
                       - lookup[(seed, world, regime, *negative)]["produced"] for world in worlds]
                      for seed in seeds]
            interval = base.crossed_interval(matrix)
            difference = float(np.mean(matrix))
            effects[label] = {"mean_products_difference": difference,
                "crossed_bootstrap_95_percent_interval": interval,
                "per_training_seed_difference": [float(np.mean(r)) for r in matrix],
                "pilot_gain_criterion_met": difference >= .25 and interval[0] > 0}
        result[regime] = {"means": means, "effects": effects}
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--training-seeds", default="17,23,41")
    p.add_argument("--corpus-episodes", type=int, default=300)
    p.add_argument("--updates", type=int, default=12000)
    p.add_argument("--worlds", type=int, default=40)
    p.add_argument("--evaluation-seed-start", type=int, default=9100000)
    p.add_argument("--regimes", default=",".join(base.REGIMES))
    p.add_argument("--agents", type=int, default=2)
    p.add_argument("--horizon", type=int, default=64)
    p.add_argument("--legacy-dir", type=Path)
    p.add_argument("--skip-legacy", action="store_true")
    p.add_argument("--output-dir", type=Path, default=Path("run/colony-diagnostics-v0-5"))
    args = p.parse_args()
    seeds, regimes = [int(s) for s in args.training_seeds.split(",")], args.regimes.split(",")
    if (not seeds or len(seeds) != len(set(seeds)) or any(s < 0 for s in seeds)
            or min(args.corpus_episodes, args.updates, args.worlds, args.agents, args.horizon) < 1
            or any(r not in base.REGIMES for r in regimes) or len(regimes) != len(set(regimes))):
        p.error("Invalid diagnostic dimensions or seeds")
    if args.skip_legacy == bool(args.legacy_dir):
        p.error("Supply exactly one of --legacy-dir or --skip-legacy")
    if any(sources()[name] != digest for name, digest in ORIGINAL_SOURCES.items()):
        raise AssertionError("Original v0.4 source was changed")
    worlds = list(range(args.evaluation_seed_start, args.evaluation_seed_start + args.worlds))
    forbidden_worlds = set(range(9000000, 9000040))
    training_worlds = {base.stable_seed("diagnostic-training-world", s, e)
                       for s in seeds for e in range(args.corpus_episodes)}
    if set(worlds) & (forbidden_worlds | training_worlds):
        raise AssertionError("Fresh held-out worlds required")
    legacy = {}
    if args.legacy_dir:
        for seed in seeds:
            if seed not in LEGACY_DIGESTS:
                p.error("Original checkpoint seed is not pinned")
            legacy[seed] = base.Network.load(args.legacy_dir / f"trained-{seed}.json")
            if legacy[seed].digest() != LEGACY_DIGESTS[seed]:
                raise AssertionError("Original checkpoint hash mismatch")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError("Output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    protocol = {"schema": SCHEMA, "sources": sources(), "numpy": np.__version__,
        "python": platform.python_version(), "observation_contract": base.observation_contract(),
        "training_seeds": seeds, "corpus_episodes": args.corpus_episodes,
        "optimizer_updates_per_variant": args.updates, "batch_size": 32,
        "target_copy_interval": 200, "learning_rate": .001, "max_backup_options": [1, 5],
        "training_action_mask": "ORIGINAL_FULL_FOR_BOTH", "alias_pruning": "EVALUATION_ONLY",
        "worlds": worlds, "regimes": regimes, "agents": args.agents, "horizon": args.horizon,
        "gamma_per_tick": GAMMA, "personal_weight": base.PERSONAL_WEIGHT,
        "behavior": "UNIFORM_RANDOM_VALID_FULL_MASK", "legacy_included": bool(legacy),
        "legacy_parameter_hashes": {str(s): m.digest() for s, m in legacy.items()},
        "primary_alias_contrast": "legacy pruned minus full on standard",
        "primary_credit_contrast": "greedy5 minus one-step, full inference mask on standard",
        "pilot_gain_criterion": "mean >=0.25 products and paired crossed-bootstrap lower bound >0",
        "credit_exposure_reporting": "actual depth distribution; do not assume five steps",
        "offline_limitation": "random-teammate data followed by greedy-team evaluation",
        "confirmatory_study": False, "minecraft_control": False}
    encoded = (json.dumps(protocol, sort_keys=True, indent=2) + "\n").encode()
    protocol_hash = hashlib.sha256(encoded).hexdigest()
    (args.output_dir / "protocol.json").write_bytes(encoded)
    all_rows, training = [], []
    for seed in seeds:
        records, corpus_stats = collect_corpus(seed, args.corpus_episodes, args.horizon, args.agents)
        corpus_bytes = b"".join(canonical_record(r) for r in records)
        (args.output_dir / f"corpus-{seed}.jsonl.gz").write_bytes(gzip.compress(corpus_bytes, mtime=0))
        models, initial, stats = train_fixed(seed, records, args.updates)
        training.append(dict(training_seed=seed, corpus=corpus_stats, variants=stats))
        for name in list(models):
            models[name] = save_reload(models[name], args.output_dir / f"{name}-{seed}.json",
                                       protocol_hash, name)
        models["untrained"] = save_reload(initial, args.output_dir / f"untrained-{seed}.json",
                                           protocol_hash, "untrained")
        if seed in legacy:
            models["legacy_online"] = legacy[seed]
            # Preserve the exact input bytes in this external result bundle.
            (args.output_dir / f"legacy-trained-{seed}.json").write_bytes(
                (args.legacy_dir / f"trained-{seed}.json").read_bytes())
        rows, examples = evaluate(models, worlds, regimes, args.agents, args.horizon)
        all_rows.extend(dict(training_seed=seed, **r) for r in rows)
        (args.output_dir / f"examples-{seed}.json").write_text(
            json.dumps(examples, separators=(",", ":"), allow_nan=False) + "\n")
        print(json.dumps({"seed": seed, "transitions": len(records),
                          "updates_each": args.updates,
                          "greedy5_mean_depth": stats["offline_greedy5"]["mean_backup_options"]}), flush=True)
    report = {"schema": SCHEMA, "origin": "ABSTRACT_SIMULATOR_ONLY", "protocol_sha256": protocol_hash,
        "training": training, "legacy_included": bool(legacy), "evaluation_frozen": True,
        "minecraft_control": False, "summary": summarize(all_rows, seeds, worlds), "runs": all_rows}
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"report": str(args.output_dir / "report.json"), "summary": report["summary"]}), flush=True)


if __name__ == "__main__":
    main()
