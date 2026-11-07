#!/usr/bin/env python3
"""Train frozen 10-16-3 MLP on SYNTHETIC report/outcome pairs, never Forge.

The simulator generates reports and hidden binary pickup success for both
candidate sources. This is SUPERVISED one-step synthetic outcome regression,
not online RL and not Minecraft training. The policy receives ONLY the report
features; hidden success is used as a simulator training target/evaluation
oracle and cannot be passed to Java inference.

No torch/numpy dependency. Output is deterministic for a fixed Python version
and seed and must be fully created before a Forge evaluation server starts.
"""
import argparse
import hashlib
import json
import math
import random
from pathlib import Path

SEED = 20261107
HELDOUT = 20361107
INPUT = 10
HIDDEN = 16
OUTPUT = 3
FEATURES = "present,wheat_norm,delivery_age_norm,observation_age_norm,revision_norm"
SCHEMA = "hearthbound.report-choice-mlp.v1"
ORIGIN = "SIMULATED_SUPERVISED_OUTCOMES_ONLY"
TRAIN_SAMPLES = 18000
EPOCHS = 5
EVAL_EPISODES = 1600


def make_sample(rng):
    slots = []
    x = []
    for _ in range(2):
        # Independent source reports; no key, coordinates, raw world identity,
        # real Forge data, or hidden pickup result in the observation.
        present = rng.random() < 0.84
        wheat = rng.randint(1, 8) if present else 0
        age = rng.randint(0, 200) if present else 0
        lag = rng.randint(0, 40) if present else 0
        revision = rng.randint(1, 8) if present else 0
        x.extend((float(present), wheat / 8.0, age / 200.0,
                  (age + lag) / 240.0, revision / 16.0))
        # Hidden environment transition: the probability that a previously
        # reported stock can still yield a physical pickup by decision time.
        p = ((0.35 + 0.10 * wheat)
             * math.exp(-1.70 * age / 200.0)
             * math.exp(-0.35 * lag / 40.0)) if present else 0.0
        slots.append((present, wheat, p))
    # The synthetic simulator CAN independently sample both potential actions.
    # These are synthetic targets only, NEVER inferred Forge counterfactuals.
    simulated_rewards = [
        ((1.0 if rng.random() < p else -0.5) if present else -0.7)
        for present, _, p in slots
    ] + [0.0]
    return x, simulated_rewards, slots


class Network:
    def __init__(self, seed):
        rng = random.Random(seed)
        self.w1 = [[rng.uniform(-0.18, 0.18) for _ in range(INPUT)]
                   for _ in range(HIDDEN)]
        self.b1 = [0.0] * HIDDEN
        self.w2 = [[rng.uniform(-0.18, 0.18) for _ in range(HIDDEN)]
                   for _ in range(OUTPUT)]
        self.b2 = [0.0] * OUTPUT

    def forward(self, x):
        if len(x) != INPUT or not all(math.isfinite(v) for v in x):
            raise ValueError("Invalid simulated observation")
        h = [math.tanh(sum(w*v for w, v in zip(row, x)) + bias)
             for row, bias in zip(self.w1, self.b1)]
        scores = [sum(w*v for w, v in zip(row, h)) + bias
                  for row, bias in zip(self.w2, self.b2)]
        return h, scores

    def update(self, x, target, rate=0.012):
        h, scores = self.forward(x)
        errors = [max(-2.0, min(2.0, y-t))
                  for y, t in zip(scores, target)]
        # All hidden gradients must be computed using the OLD second-layer
        # weights, before any parameter changes.
        dh = [(1.0 - h[i]*h[i])
              * sum(errors[o] * self.w2[o][i] for o in range(OUTPUT))
              for i in range(HIDDEN)]
        for o in range(OUTPUT):
            for i in range(HIDDEN):
                self.w2[o][i] -= rate * errors[o] * h[i]
            self.b2[o] -= rate * errors[o]
        for i in range(HIDDEN):
            for j in range(INPUT):
                self.w1[i][j] -= rate * dh[i] * x[j]
            self.b1[i] -= rate * dh[i]


def predict(model, x):
    # Two absent reports are an invalid choose action regardless of logits.
    if x[0] == 0.0 and x[5] == 0.0:
        return 2
    logits = model.forward(x)[1]
    # Unreported candidate may NEVER be selected from optimistic weights.
    if x[0] == 0.0:
        logits[0] = float("-inf")
    if x[5] == 0.0:
        logits[1] = float("-inf")
    return max(range(OUTPUT), key=lambda i: (logits[i], -i))


def scripted(x):
    stock_a = x[1] if x[0] else -1.0
    stock_b = x[6] if x[5] else -1.0
    if stock_a < 0 and stock_b < 0:
        return 2
    return 0 if stock_a >= stock_b else 1


def evaluate(model, seed=HELDOUT, episodes=EVAL_EPISODES):
    rng = random.Random(seed)
    counts = {"mlp": [0.0, 0, 0], "scripted": [0.0, 0, 0],
              "abstain": [0.0, 0, 0]}
    decisions = []
    for _ in range(episodes):
        x, actual, _ = make_sample(rng)
        arms = {"mlp": predict(model, x), "scripted": scripted(x),
                "abstain": 2}
        decisions.append(arms["mlp"] != arms["scripted"])
        for name, decision in arms.items():
            counts[name][0] += actual[decision]
            counts[name][1] += int(decision != 2)
            counts[name][2] += int(decision != 2 and actual[decision] > 0)
    return {
        name: {"mean_simulated_reward": round(val[0]/episodes, 5),
               "choose_rate": round(val[1]/episodes, 5),
               "successful_synthetic_pickup_rate": round(val[2]/episodes, 5)}
        for name, val in counts.items()
    } | {"model_scripted_disagreement_rate": round(sum(decisions)/episodes, 5)}


def serialize(model):
    lines = [
        SCHEMA, "origin=" + ORIGIN, "training_seed=" + str(SEED),
        "training_samples=" + str(TRAIN_SAMPLES),
        "heldout_seed=" + str(HELDOUT),
        "features=" + FEATURES, "dimensions=10,16,3",
    ]
    values = [
        ("w1", [v for row in model.w1 for v in row]),
        ("b1", model.b1),
        ("w2", [v for row in model.w2 for v in row]),
        ("b2", model.b2),
    ]
    for name, elements in values:
        lines.append(name + "=" + ",".join(format(v, ".12g") for v in elements))
    return ("\n".join(lines) + "\n").encode("utf-8")


def train():
    model = Network(SEED)
    rng = random.Random(SEED + 1)
    dataset = [make_sample(rng) for _ in range(TRAIN_SAMPLES)]
    for epoch in range(EPOCHS):
        order = list(range(TRAIN_SAMPLES))
        random.Random(SEED + 100 + epoch).shuffle(order)
        for idx in order:
            x, targets, _ = dataset[idx]
            model.update(x, targets)
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=Path("run/report-choice-mlp-v1.txt"))
    parser.add_argument("--sha", type=Path, default=Path("run/report-choice-mlp-v1.sha256"))
    parser.add_argument("--report", type=Path, default=Path("report-choice-mlp-training.json"))
    args = parser.parse_args()
    model = train()
    data = serialize(model)
    digest = hashlib.sha256(data).hexdigest()
    evaluation = evaluate(model)
    # Independent synthetic checks, never Forge-grounded claims.
    if evaluation["mlp"]["choose_rate"] < 0.10 or evaluation["mlp"]["choose_rate"] > 0.96:
        raise AssertionError("Degenerate learned policy selection coverage")
    if not all(math.isfinite(v) for row in model.w1 + model.w2 for v in row):
        raise AssertionError("Non-finite trained model")
    result = {
        "schema": "hearthbound.report-mlp-training-report.v1",
        "origin": ORIGIN,
        "training_seed": SEED,
        "heldout_seed": HELDOUT,
        "training_samples": TRAIN_SAMPLES,
        "training_epochs": EPOCHS,
        "heldout_samples": EVAL_EPISODES,
        "observations_include_real_minecraft_inventory": False,
        "forge_test_data_used_in_training": False,
        "model_is_frozen_before_forge": True,
        "supervised_simulated_outcomes_not_reinforcement_learning": True,
        "model_sha256": digest,
        "heldout": evaluation,
    }
    for path in (args.model, args.sha, args.report):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.model.write_bytes(data)
    args.sha.write_text(digest + "\n", encoding="utf-8")
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("SIMULATED_REPORT_MLP_TRAINED", json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
