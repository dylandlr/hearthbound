#!/usr/bin/env python3
"""Multi-seed, paired, held-out robustness evaluation of simulator attention.

A research-only analysis. No Minecraft execution or live policy deployment.
Distinct evaluation seeds from training; identical latent episodes for policy
comparisons. Bootstrap resamples paired episode differences, not observations.
"""
import argparse
import hashlib
import json
import math
import random
from pathlib import Path
import train_simulated_attention_mlp as base

SCHEMA = "hearthbound.simulated-attention-robustness.v1"
HORIZON = 32

def make_world(seed, regime):
    world = base.World(seed)
    if regime == "in_distribution":
        return world
    if regime == "high_volatility":
        # Defined before any policy observes; still hypothetical known metadata.
        world.volatility = [min(.95, v * 2.0) for v in world.volatility]
    elif regime == "low_volatility":
        world.volatility = [max(.005, v * .25) for v in world.volatility]
    elif regime == "unequal_volatility":
        # Fixed source-specific volatility profile, independent of latent truth.
        world.volatility = [.015, .08, .45, .9]
    else:
        raise ValueError("unknown evaluation regime")
    return world

def policy_score(seed, regime, policy, model=None):
    world = make_world(seed, regime)
    reward, discoveries = 0.0, 0
    for _ in range(HORIZON):
        action = base.scripted(world) if policy == "scripted" else base.learned(model, world)
        earned, found = world.inspect(action)
        reward += earned
        discoveries += int(found)
    return {"reward": round(reward, 10), "discoveries": discoveries}

def paired_samples(model, evaluation_seeds, regime):
    pairs = []
    for seed in evaluation_seeds:
        scripted = policy_score(seed, regime, "scripted")
        learned = policy_score(seed, regime, "learned", model)
        pairs.append({
            "seed": seed,
            "scripted_discoveries": scripted["discoveries"],
            "learned_discoveries": learned["discoveries"],
            "delta_discoveries": learned["discoveries"] - scripted["discoveries"],
            "scripted_reward": scripted["reward"],
            "learned_reward": learned["reward"],
            "delta_reward": round(learned["reward"] - scripted["reward"], 10)
        })
    return pairs

def percentile(sorted_values, fraction):
    at = fraction * (len(sorted_values) - 1)
    low = int(math.floor(at))
    high = int(math.ceil(at))
    return sorted_values[low] * (high - at) + sorted_values[high] * (at - low)

def interval(values, bootstrap_seed, iterations):
    if not values or iterations < 10:
        raise ValueError("need values and >=10 bootstrap replicates")
    rng = random.Random(bootstrap_seed)
    n = len(values)
    means = []
    for _ in range(iterations):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    mean = sum(values) / n
    return {
        "mean": round(mean, 6),
        "bootstrap_95_ci": [round(percentile(means, .025), 6),
                            round(percentile(means, .975), 6)],
        "n_paired_episodes": n,
        "bootstrap_replicates": iterations
    }

def benchmark(train_seeds=(11, 17, 23), train_episodes=500,
              eval_episodes=100, bootstrap_replicates=500):
    if len(set(train_seeds)) != len(train_seeds) or not train_seeds:
        raise ValueError("independent unique training seeds required")
    if train_episodes < 1 or eval_episodes < 1 or bootstrap_replicates < 10:
        raise ValueError("invalid evaluation budget")
    regimes = ("in_distribution", "high_volatility", "low_volatility",
               "unequal_volatility")
    results = []
    for train_seed in train_seeds:
        model = base.MLP(train_seed)
        rng = random.Random(train_seed + 7)
        for episode in range(train_episodes):
            world = base.World(1000000 + train_seed * 100000 + episode)
            epsilon = .08 + .75 * max(0., 1. - episode / max(1, train_episodes * .8))
            for _ in range(HORIZON):
                x = world.features()
                action = rng.randrange(base.SOURCES) if rng.random() < epsilon else base.learned(model, world)
                reward, _ = world.inspect(action)
                model.update(x, action, reward)
        for regime_id, regime in enumerate(regimes):
            # The same held-out worlds for baseline and trained model.
            # Separate from training worlds and independent across training seeds.
            eval_seeds = [90000000 + train_seed * 100000 + i for i in range(eval_episodes)]
            pairs = paired_samples(model, eval_seeds, regime)
            delta = interval([r["delta_discoveries"] for r in pairs],
                             train_seed * 100 + regime_id, bootstrap_replicates)
            delta_reward = interval([r["delta_reward"] for r in pairs],
                                    train_seed * 100 + regime_id + 10000, bootstrap_replicates)
            results.append({
                "train_seed": train_seed,
                "regime": regime,
                "scripted_mean_discoveries": round(sum(r["scripted_discoveries"] for r in pairs) / eval_episodes, 6),
                "trained_mean_discoveries": round(sum(r["learned_discoveries"] for r in pairs) / eval_episodes, 6),
                "paired_discovery_difference": delta,
                "paired_reward_difference": delta_reward
            })
    result = {
        "schema": SCHEMA,
        "origin": "SIMULATED_ONLY",
        "training_seeds": list(train_seeds),
        "train_episodes_per_seed": train_episodes,
        "heldout_episodes_per_seed_regime": eval_episodes,
        "observations_per_decision": 1,
        "bootstrap_method": "paired episode bootstrap, within training seed and regime",
        "bootstrap_replicates": bootstrap_replicates,
        "minecraft_policy_deployed": False,
        "minecraft_learning_claimed": False,
        "citizen_actions_authorized": False,
        "regimes": list(regimes),
        "results": results,
        "caveats": [
            "Synthetic worlds: results do not demonstrate Minecraft learning",
            "No aggregate CI pooling across independently trained models",
            "Volatility remains known synthetic metadata, unavailable as ground truth in Minecraft",
            "Bootstrap CI only captures held-out episode variance within each training seed",
            "Hyperparameter selection must not use the evaluation seeds",
            "No navigation, social learning, action dispatch, or live inventory authority"
        ]
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",",":"), allow_nan=False)
    result["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 17, 23])
    parser.add_argument("--train-episodes", type=int, default=500)
    parser.add_argument("--heldout", type=int, default=100)
    parser.add_argument("--bootstrap", type=int, default=500)
    parser.add_argument("--output", type=Path, default=Path("simulated-attention-robustness.json"))
    args = parser.parse_args()
    result = benchmark(tuple(args.seeds), args.train_episodes, args.heldout, args.bootstrap)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for entry in result["results"]:
        d = entry["paired_discovery_difference"]
        print("ATTENTION_ROBUSTNESS",
              "seed="+str(entry["train_seed"]),
              "regime="+entry["regime"],
              "delta="+str(d["mean"]),
              "ci="+str(d["bootstrap_95_ci"]),
              "origin=SIMULATED_ONLY")
    print("SIMULATED_ATTENTION_ROBUSTNESS_COMPLETE sha256="+result["sha256"])

if __name__ == "__main__":
    main()
