#!/usr/bin/env python3
"""Turn independently verified Forge Minecraft outcomes into reward-labeled data.

This is OFFLINE evidence labeling, not online reinforcement learning or training.
No reward is granted to the game or to Sable by this script.
"""
import argparse
import hashlib
import json
from pathlib import Path

TRIAL="hearthbound.real-minecraft-policy-trial.v1"
SHADOW="hearthbound.live-shadow-evidence.v2"
SEED="hearthbound-policy-v0-8-10"
ACTIONS={"INSPECT_UNPOWERED", "COLLECT_OUTPUT", "WAIT_FOR_PROCESSING", "REQUEST_WHEAT_HAUL"}
POLICIES={"SCRIPTED", "TRAINED_MLP"}

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def build(trial, shadow, *, restart_verified, trial_digest, shadow_digest):
    policy=trial.get("policy")
    require(policy in POLICIES, "Unknown trial policy")
    require(trial.get("schema")==TRIAL and shadow.get("schema")==SHADOW, "Incorrect evidence schema")
    require(trial.get("source")=="live Forge dedicated-server RCON", "Trial not from real game")
    require(shadow.get("read_only") is True, "Shadow policy did not run read-only")
    require(trial.get("existing_executor")=="SableHauling", "Unknown authorized executor")
    require(trial.get("completion") is True and trial.get("observed_flour") is True,
            "Cannot award completion reward without real flour and task completion")
    require(type(trial.get("verified_citizen_experience")) is int
            and trial["verified_citizen_experience"]==1,
            "Missing verified Sable memory increment")
    require(restart_verified is True, "Persistent memory was not verified after restart")
    ticks=trial.get("minecraft_elapsed_ticks")
    require(type(ticks) is int and 1<=ticks<=20000, "Invalid Minecraft duration")
    require(trial.get("rl_or_adaptation_demonstrated") is False,
            "Imported trial falsely claims adaptation")
    require(shadow.get("learning_improvement_demonstrated") is False,
            "Imported shadow falsely claims learning")
    require(shadow.get("disagreements")==0 and shadow.get("masked")==0,
            "Unexpected shadow disagreements or masked actions")
    stages=shadow.get("stages")
    require(isinstance(stages,dict) and set(stages)=={
        "empty_powered","output_ready","citizen_experienced"
    }, "Missing verified world states")
    start=stages["empty_powered"]
    finish=stages["citizen_experienced"]
    require(start.get("scripted")=="REQUEST_WHEAT_HAUL"
            and start.get("trained")=="REQUEST_WHEAT_HAUL"
            and start.get("raw_model")=="REQUEST_WHEAT_HAUL"
            and start.get("experience")==0 and start.get("powered") is True
            and start.get("flour")==0, "Invalid observed task precondition")
    require(finish.get("experience")==1 and finish.get("flour",0)>=1,
            "Missing outcome observation")
    require(all(stage.get("disagreement") is False and stage.get("masked") is False
                for stage in stages.values()), "Unsafe or inconsistent shadow observation")
    action=start["scripted"] if policy=="SCRIPTED" else start["trained"]
    require(action in ACTIONS and action=="REQUEST_WHEAT_HAUL", "Invalid policy-selected action")

    # Explicit, documented bookkeeping rewards; neither is a measured neural
    # prediction nor a claim of counterfactual advantage. 201 ticks => -0.201.
    # No safety penalty is assigned without a separately observed violation.
    efficiency_penalty=round(ticks/1000.0,6)
    return {
        "schema":"hearthbound.minecraft-experience-transition.v1",
        "source":"verified dedicated Forge/Create Minecraft experiment",
        "provenance":{
            "trial_sha256":trial_digest,
            "shadow_sha256":shadow_digest,
            "world_seed":SEED,
            "restarted_memory_verified":True,
            "model_artifact":"mill-mlp-v1",
            "policy":policy,
        },
        "observation":{
            "powered":True,
            "wheat_present":False,
            "flour_present":False,
            "blocked":False,
            "verified_experience":0,
        },
        "selected_action":action,
        "reward_contract":"hearthbound.mill-reward.v1",
        "rewards":{
            "colony":{
                "flour_produced_success":1.0,
                "time_cost":-efficiency_penalty,
                "total":round(1.0-efficiency_penalty,6),
            },
            "personal":{
                "verified_task_completion":0.5,
                "verified_new_experience":0.5,
                "total":1.0,
            },
        },
        "outcome":{
            "completed":True,
            "flour_observed":True,
            "verified_experience_after":1,
            "minecraft_elapsed_ticks":ticks,
            "terminal":True,
        },
        "limitations":{
            "offline_reward_label_not_rl_training":True,
            "single_trajectory_not_policy_comparison":True,
            "no_counterfactual_action_value":True,
            "no_live_reward_grant":True,
        }
    }

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("trial",type=Path)
    p.add_argument("shadow",type=Path)
    p.add_argument("--restart-log",type=Path,required=True)
    p.add_argument("--output",type=Path,default=Path("minecraft-experience.json"))
    args=p.parse_args()
    restart=args.restart_log.read_text(encoding="utf-8",errors="replace")
    require(restart.count("SABLE_VERIFIED_EXPERIENCE_SURVIVED_REAL_SERVER_RESTART")==1,
            "Missing or duplicated verified server restart receipt")
    transition=build(json.loads(args.trial.read_text()),
                     json.loads(args.shadow.read_text()),
                     restart_verified=True,trial_digest=sha256(args.trial),
                     shadow_digest=sha256(args.shadow))
    args.output.write_text(json.dumps(transition,indent=2,sort_keys=True)+"\n")
    print("VERIFIED_MINECRAFT_EXPERIENCE",json.dumps(transition,sort_keys=True))

if __name__=="__main__":
    main()
