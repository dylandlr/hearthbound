#!/usr/bin/env python3
"""Reproducible supervised imitation of a scripted Hearthbound task selector.

Synthetic one-step scenarios only. NOT reinforcement learning or actual Minecraft.
"""
import argparse, json, random
from dataclasses import dataclass
import numpy as np
import torch
from torch import nn

ACTIONS = ('eat', 'rest', 'collect_wheat', 'mill_wheat', 'wait')
@dataclass(frozen=True)
class Scenario:
    hunger: float
    fatigue: float
    wheat: float
    mill_powered: float
    threat: float
    travel: float
    def observation(self):
        return np.array([self.hunger, self.fatigue, self.wheat,
                         self.mill_powered, self.threat, self.travel], dtype=np.float32)

def sample(seed, n, heldout=False):
    rng = np.random.default_rng(seed)
    return [Scenario(float(rng.uniform(0,1)), float(rng.uniform(0,1)),
                     float(rng.integers(0,3)/2), float(rng.integers(0,2)),
                     float(rng.beta(2,2) if not heldout else rng.beta(.7,.7)),
                     float(rng.uniform(0,.7) if not heldout else rng.uniform(.35,1)))
            for _ in range(n)]

def expert(s):
    if s.threat >= .78: return 4
    if s.hunger >= .73: return 0
    if s.fatigue >= .77: return 1
    if s.wheat >= .5 and s.mill_powered >= .5: return 3
    if s.wheat < .5 and s.travel < .83: return 2
    return 4

def evaluate(scenarios, choose):
    predictions = [int(choose(s.observation(), s)) for s in scenarios]
    labels = [expert(s) for s in scenarios]
    safety = sum(s.threat >= .78 and p != 4 for s,p in zip(scenarios,predictions))
    correct = sum(p == y for p,y in zip(predictions,labels))
    return {'count':len(scenarios),'correct':correct,
            'accuracy':round(correct/len(scenarios),4),
            'mean_proxy_reward':round((correct-safety)/len(scenarios),4),
            'safety_violations':safety}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=20261102)
    parser.add_argument('--train-size',type=int,default=12000)
    parser.add_argument('--test-size',type=int,default=3000)
    parser.add_argument('--epochs',type=int,default=35)
    parser.add_argument('--output',default='policy-results.json')
    a = parser.parse_args()
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    torch.set_num_threads(1)
    train = sample(a.seed,a.train_size)
    heldout = sample(a.seed+1000003,a.test_size,True)
    x = torch.tensor(np.stack([s.observation() for s in train]))
    y = torch.tensor([expert(s) for s in train],dtype=torch.long)
    def make_model():
        return nn.Sequential(nn.Linear(6,48),nn.ReLU(),nn.Linear(48,48),
                             nn.ReLU(),nn.Linear(48,len(ACTIONS)))
    fresh = make_model()
    trained = make_model()
    trained.load_state_dict(fresh.state_dict())
    optim = torch.optim.Adam(trained.parameters(),lr=.003)
    for epoch in range(a.epochs):
        for idx in torch.randperm(len(x)).split(256):
            optim.zero_grad()
            loss = nn.functional.cross_entropy(trained(x[idx]),y[idx])
            loss.backward(); optim.step()
    def choose(model):
        model.eval()
        def predict(obs,_):
            with torch.no_grad():
                return model(torch.from_numpy(obs)).argmax().item()
        return predict
    results = {'schema':'hearthbound.policy-imitation-benchmark.v1',
        'scope':'synthetic partially observable task-selection proxy; NOT Minecraft or RL',
        'seed':a.seed,'train_size':a.train_size,'heldout_size':a.test_size,
        'epochs':a.epochs,'actions':ACTIONS,
        'scripted_expert':evaluate(heldout,lambda obs,s:expert(s)),
        'untrained_mlp':evaluate(heldout,choose(fresh)),
        'imitation_trained_mlp':evaluate(heldout,choose(trained))}
    with open(a.output,'w') as f:json.dump(results,f,indent=2)
    print(json.dumps(results,indent=2))
    assert results['imitation_trained_mlp']['accuracy'] > results['untrained_mlp']['accuracy']

if __name__ == '__main__': main()
