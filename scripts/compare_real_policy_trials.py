#!/usr/bin/env python3
"""Compare two *verified* real Minecraft policy trial artifacts.

Requires both arms, same experiment contract and valid observations.
A single trial per arm is descriptive only: do not infer improvement.
"""
import argparse
import json
from pathlib import Path

SCHEMA="hearthbound.real-minecraft-policy-trial.v1"
POLICIES=("SCRIPTED","TRAINED_MLP")

def validate(data, expected):
    if data.get("schema") != SCHEMA or data.get("policy") != expected:
        raise ValueError("Wrong real-Minecraft trial schema or policy for " + expected)
    if data.get("source") != "live Forge dedicated-server RCON":
        raise ValueError("Not a verified Forge trial record")
    if data.get("existing_executor") != "SableHauling":
        raise ValueError("Unknown gameplay executor")
    if data.get("completion") is not True or data.get("observed_flour") is not True:
        raise ValueError("Missing real Minecraft task completion or flour")
    if type(data.get("verified_citizen_experience")) is not int or data["verified_citizen_experience"] != 1:
        raise ValueError("Missing Sable's verified experience")
    ticks=data.get("minecraft_elapsed_ticks")
    if type(ticks) is not int or not 1<=ticks<=20000:
        raise ValueError("Invalid Minecraft game tick duration")
    if data.get("comparative_advantage_demonstrated") is not False:
        raise ValueError("Single-arm record must not claim advantage")
    if data.get("rl_or_adaptation_demonstrated") is not False:
        raise ValueError("Single-arm record must not claim RL or adaptation")
    return ticks

def compare(scripted, mlp):
    scripted_ticks=validate(scripted,"SCRIPTED")
    mlp_ticks=validate(mlp,"TRAINED_MLP")
    return {
        "schema":"hearthbound.real-minecraft-policy-comparison.v1",
        "origin":"two independent dedicated Forge/Create server trials",
        "episodes_per_arm":1,
        "observations_are_real_minecraft":True,
        "same_starting_fixture_intended":True,
        "identical_agent_rng_guaranteed":False,
        "scripted":{"completed":True,"minecraft_elapsed_ticks":scripted_ticks},
        "trained_mlp":{"completed":True,"minecraft_elapsed_ticks":mlp_ticks},
        "trained_minus_scripted_ticks":mlp_ticks-scripted_ticks,
        "statistical_significance_claimed":False,
        "policy_superiority_claimed":False,
        "minecraft_reward_learning_claimed":False,
        "interpretation":"Two successful isolated one-shot task proofs; no generalization, RL, or statistical superiority inference"
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("scripted",type=Path)
    p.add_argument("trained_mlp",type=Path)
    p.add_argument("--output",type=Path,default=Path("policy-comparison.json"))
    args=p.parse_args()
    result=compare(json.loads(args.scripted.read_text()),json.loads(args.trained_mlp.read_text()))
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print("VERIFIED_REAL_POLICY_COMPARISON",json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
