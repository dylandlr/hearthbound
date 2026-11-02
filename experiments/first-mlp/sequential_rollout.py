#!/usr/bin/env python3
"""Sequential Hearthbound surrogate, not Minecraft or a real citizen policy.

Policies make repeated decisions. Actions mutate state; reward measures outcomes.
Training still uses scripted imitation so this is *evaluation*, not RL training.
"""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

spec = importlib.util.spec_from_file_location("baseline", Path(__file__).with_name("policy_experiment.py"))
base = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = base
spec.loader.exec_module(base)

def make_model():
    return nn.Sequential(nn.Linear(6, 48), nn.ReLU(), nn.Linear(48, 48),
                         nn.ReLU(), nn.Linear(48, len(base.ACTIONS)))

def train(seed, n=12000, epochs=35):
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    samples = base.sample(seed, n)
    x = torch.tensor(np.stack([s.observation() for s in samples]))
    y = torch.tensor([base.expert(s) for s in samples], dtype=torch.long)
    random_policy = make_model()
    policy = make_model()
    policy.load_state_dict(random_policy.state_dict())
    opt = torch.optim.Adam(policy.parameters(), lr=0.003)
    for _ in range(epochs):
        for batch in torch.randperm(n).split(256):
            opt.zero_grad()
            loss = nn.functional.cross_entropy(policy(x[batch]), y[batch])
            loss.backward()
            opt.step()
    return random_policy.eval(), policy.eval()

class ColonyEpisode:
    """Single-citizen, 60-tick Markov surrogate with limited observations."""
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.hunger = float(self.rng.uniform(.30, .65))
        self.fatigue = float(self.rng.uniform(.15, .55))
        self.wheat = 0
        self.power = bool(self.rng.integers(0, 2))
        self.threat = float(self.rng.uniform(0, .5))
        self.travel = float(self.rng.uniform(.25, .90))
        self.flour = self.waste = self.unsafe = 0
        self.ticks = 0

    def scenario(self):
        return base.Scenario(self.hunger, self.fatigue, float(self.wheat),
                             float(self.power), self.threat, self.travel)
    def step(self, action):
        if not 0 <= action < len(base.ACTIONS):
            raise ValueError("invalid high-level action")
        self.ticks += 1
        self.hunger = min(1., self.hunger + .035)
        self.fatigue = min(1., self.fatigue + .022)
        if self.threat >= .78 and action != 4:
            self.unsafe += 1
        if action == 0:  # food from a shared colony supply, finite action cost
            self.hunger = max(0., self.hunger - .55)
        elif action == 1:
            self.fatigue = max(0., self.fatigue - .55)
        elif action == 2:
            if self.wheat == 0 and self.travel < .83 and self.threat < .78:
                self.wheat = 1
            else:
                self.waste += 1
        elif action == 3:
            if self.wheat and self.power and self.threat < .78:
                self.wheat = 0
                self.flour += 1
            else:
                self.waste += 1
        elif action == 4:
            self.threat = max(0., self.threat - .10)
        self.threat = float(np.clip(self.threat + self.rng.normal(0, .065), 0, 1))
        if self.ticks % 8 == 0:
            self.power = bool(self.rng.random() < .75)
            self.travel = float(self.rng.uniform(.2, 1))
        return self.flour

def rollout(policy, seeds, steps=60):
    results = []
    for seed in seeds:
        env = ColonyEpisode(seed)
        for _ in range(steps):
            action = int(policy(env.scenario()))
            env.step(action)
        results.append({"flour":env.flour,"unsafe":env.unsafe,"waste":env.waste,
                        "hunger":env.hunger,"fatigue":env.fatigue})
    return {
        "episodes":len(results),
        "mean_flour":round(float(np.mean([e["flour"] for e in results])),4),
        "mean_unsafe_actions":round(float(np.mean([e["unsafe"] for e in results])),4),
        "mean_wasted_actions":round(float(np.mean([e["waste"] for e in results])),4),
        "mean_end_hunger":round(float(np.mean([e["hunger"] for e in results])),4),
        "completion_rate_at_least_one_flour":round(float(np.mean([e["flour"]>0 for e in results])),4)
    }

def choose_mlp(model):
    def choose(s):
        with torch.no_grad():
            return model(torch.from_numpy(s.observation())).argmax().item()
    return choose

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seed",type=int,default=20261102)
    ap.add_argument("--episodes",type=int,default=300)
    ap.add_argument("--steps",type=int,default=60)
    ap.add_argument("--output",type=Path,default=Path("sequential-results.json"))
    args=ap.parse_args()
    if args.episodes < 1 or args.steps < 1: ap.error("episodes and steps must be positive")
    random_policy, imitation_policy=train(args.seed)
    # Paired held-out episode seeds, no privileged access to physical state.
    seeds=[args.seed+1000003+97*i for i in range(args.episodes)]
    report={"schema":"hearthbound.sequential-surrogate.v1",
            "scope":"synthetic closed-loop task outcomes; no Minecraft and no RL training",
            "seed":args.seed,"steps":args.steps,
            "scripted":rollout(base.expert,seeds,args.steps),
            "untrained_mlp":rollout(choose_mlp(random_policy),seeds,args.steps),
            "imitation_mlp":rollout(choose_mlp(imitation_policy),seeds,args.steps)}
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
