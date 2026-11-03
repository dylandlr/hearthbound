#!/usr/bin/env python3
"""Aggregate independently verified real-game transition records; no training."""
import argparse
import json
from pathlib import Path

def aggregate(scripted, trained):
    records={"SCRIPTED":scripted,"TRAINED_MLP":trained}
    for mode,row in records.items():
        if row.get("schema")!="hearthbound.minecraft-experience-transition.v1":
            raise ValueError("Incorrect experience transition schema")
        provenance=row.get("provenance",{})
        if provenance.get("policy")!=mode or provenance.get("restarted_memory_verified") is not True:
            raise ValueError("Missing verified policy or post-restart evidence")
        if provenance.get("world_seed")!="hearthbound-policy-v0-8-10":
            raise ValueError("World seed mismatch")
        if row.get("selected_action")!="REQUEST_WHEAT_HAUL":
            raise ValueError("Unsupported transition action")
        outcome=row.get("outcome",{})
        if outcome.get("completed") is not True or outcome.get("flour_observed") is not True:
            raise ValueError("Incomplete actual Minecraft task")
        if outcome.get("verified_experience_after")!=1:
            raise ValueError("Missing verified Sable memory")
        rewards=row.get("rewards",{})
        for reward_type in ("colony","personal"):
            values=rewards.get(reward_type,{})
            if type(values.get("total")) not in (float,int):
                raise ValueError("Missing " + reward_type + " reward")
        if row.get("limitations",{}).get("offline_reward_label_not_rl_training") is not True:
            raise ValueError("Unsupported claim of online learning")
    return {
        "schema":"hearthbound.minecraft-reward-dataset.v1",
        "source":"two successful independent Forge/Create trials with verified persistence",
        "training_performed":False,
        "episodes_per_policy":1,
        "statistical_comparison_supported":False,
        "transitions":[scripted,trained],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("scripted",type=Path)
    p.add_argument("trained",type=Path)
    p.add_argument("--output",type=Path,default=Path("minecraft-experience-dataset.json"))
    a=p.parse_args()
    dataset=aggregate(json.loads(a.scripted.read_text()),json.loads(a.trained.read_text()))
    a.output.write_text(json.dumps(dataset,indent=2,sort_keys=True)+"\n")
    print("VERIFIED_MINECRAFT_REWARD_DATASET",
          json.dumps({"schema":dataset["schema"],"n":len(dataset["transitions"]),
                      "training_performed":False},sort_keys=True))
if __name__=="__main__":
    main()
