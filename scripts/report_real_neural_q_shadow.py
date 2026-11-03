#!/usr/bin/env python3
"""Audit offline neural Q predictions over authentic Minecraft RCON states.

This evaluates simulator-trained predictions ONLY. It never dispatches actions.
"""
import argparse
import json
import math
import re
from pathlib import Path

ACTIONS=("INSPECT_SOURCE","WAIT_FOR_SUPPLY","REQUEST_WHEAT_HAUL")
EXPECTED={"empty":"WAIT_FOR_SUPPLY","unknown":"INSPECT_SOURCE",
          "available":"REQUEST_WHEAT_HAUL"}
PATTERN=re.compile(
    r"^NEURAL_Q_REAL_SHADOW arm=(SCRIPTED|TRAINED_MLP)"
    r" stage=(empty|unknown|available)"
    r" neural=([A-Z_]+) reference=([A-Z_]+)"
    r" q=([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+)"
    r" checkpoint=([a-f0-9]{64}) simulator_trained=true read_only=true dispatch=false$"
)

def analyze(source):
    found={}
    checksums=set()
    for line in source.splitlines():
        if "NEURAL_Q_REAL_SHADOW" not in line:continue
        m=PATTERN.fullmatch(line.strip())
        if m is None:raise ValueError("Malformed or unsafe neural Minecraft shadow line")
        arm,stage,neural,reference,*other=m.groups()
        *scores,checksum=other
        if neural not in ACTIONS or reference!=EXPECTED[stage]:
            raise ValueError("Unrecognized action or invalid ground-truth reference")
        key=(arm,stage)
        if key in found:raise ValueError("Duplicated neural Minecraft prediction")
        scores=[float(x) for x in scores]
        if not all(math.isfinite(x) for x in scores):
            raise ValueError("Nonfinite Q score")
        argmax=max(range(3),key=lambda i:scores[i])
        if ACTIONS[argmax]!=neural:
            raise ValueError("Reported action does not match neural Q values")
        checksums.add(checksum)
        found[key]={"neural":neural,"reference":reference,
                    "agreement":neural==reference,"q_values":scores}
    if len(found)!=6 or len(checksums)!=1:
        raise ValueError("Require 3 states in both independent Minecraft arms and one checkpoint")
    if set(found)!={(arm,stage) for arm in ("SCRIPTED","TRAINED_MLP") for stage in EXPECTED}:
        raise ValueError("Missing policy arm or real-world state")
    results={}
    for arm in ("SCRIPTED","TRAINED_MLP"):
        results[arm]={stage:found[(arm,stage)] for stage in EXPECTED}
    if any(results["SCRIPTED"][stage]["q_values"]!=results["TRAINED_MLP"][stage]["q_values"]
           for stage in EXPECTED):
        raise ValueError("Deterministic frozen checkpoint produced different Q for matched fixture")
    return {
        "schema":"hearthbound.real-neural-q-shadow.v1",
        "model_training_origin":"SIMULATED_ONLY",
        "observation_origin":"TWO_REAL_FORGE_MINECRAFT_SERVERS",
        "checkpoint_sha256":next(iter(checksums)),
        "read_only":True,
        "game_actions_authorized":False,
        "minecraft_learning_demonstrated":False,
        "matches_per_arm":{arm:sum(v["agreement"] for v in stages.values())
                           for arm,stages in results.items()},
        "states_per_arm":3,
        "arms":results,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("scripted",type=Path)
    p.add_argument("trained_mlp",type=Path)
    p.add_argument("--output",type=Path,default=Path("real-neural-q-shadow.json"))
    a=p.parse_args()
    data=analyze(a.scripted.read_text()+"\n"+a.trained_mlp.read_text())
    a.output.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    print("VERIFIED_READ_ONLY_REAL_MINECRAFT_NEURAL_SHADOW",
          json.dumps(data,sort_keys=True))

if __name__=="__main__":main()
