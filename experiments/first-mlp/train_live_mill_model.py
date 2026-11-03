#!/usr/bin/env python3
"""Reproduce bundled 5-12-4 mill policy through supervised scripted imitation.

This is NOT RL training. Train only on synthetic states, never Minecraft outcomes.
"""
import argparse
import hashlib
import random
from pathlib import Path
import torch

SEED=20261102
def oracle(x):
    power,wheat,flour,blocked,_=x
    return 0 if power<.5 else 1 if flour>=.5 or blocked>=.5 else 2 if wheat>=.5 else 3

def train():
    torch.manual_seed(SEED)
    torch.set_num_threads(1)
    features,targets=[],[]
    for power in [0.,1.]:
        for wheat in [0.,1.]:
            for flour in [0.,1.]:
                for blocked in [0.,1.]:
                    for i in range(100):
                        exp=random.Random(SEED+i*31+int(power)*7+int(wheat)*11+
                                          int(flour)*13+int(blocked)*17).random()
                        state=[power,wheat,flour,blocked,exp]
                        features.append(state)
                        targets.append(oracle(state))
    x=torch.tensor(features,dtype=torch.float32)
    y=torch.tensor(targets)
    model=torch.nn.Sequential(torch.nn.Linear(5,12),torch.nn.ReLU(),torch.nn.Linear(12,4))
    optimizer=torch.optim.Adam(model.parameters(),lr=.02)
    for _ in range(350):
        optimizer.zero_grad()
        loss=torch.nn.functional.cross_entropy(model(x),y)
        loss.backward()
        optimizer.step()
    with torch.no_grad():
        accuracy=(model(x).argmax(-1)==y).float().mean().item()
        if accuracy<1: raise AssertionError("model did not reproduce synthetic training rules")
    tensor_parts=[model[0].weight.detach().flatten(),model[0].bias.detach(),
                  model[2].weight.detach().flatten(),model[2].bias.detach()]
    lines=["hearthbound.mill-mlp.v1",
           "features=powered,wheat_present,flour_present,blocked,experience_norm",
           "actions=INSPECT_UNPOWERED,COLLECT_OUTPUT,WAIT_FOR_PROCESSING,REQUEST_WHEAT_HAUL",
           "hidden=12"]
    for key,values in zip(["w1","b1","w2","b2"],tensor_parts):
        lines.append(key+"="+",".join(format(float(value),".9g") for value in values))
    return ("\n".join(lines)+"\n").encode()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=Path("src/main/resources/hearthbound/policy/mill-mlp-v1.txt"))
    args=ap.parse_args()
    data=train()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(data)
    print("Model SHA256:",hashlib.sha256(data).hexdigest())

if __name__=="__main__":
    main()
