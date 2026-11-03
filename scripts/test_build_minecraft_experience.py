#!/usr/bin/env python3
"""Strict reward-evidence checks. Synthetic fixtures here are not game evidence."""
import copy
import importlib.util
from pathlib import Path

path=Path(__file__).with_name("build_minecraft_experience.py")
spec=importlib.util.spec_from_file_location("minecraft_experience",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def sample(policy):
    trial={
        "schema":"hearthbound.real-minecraft-policy-trial.v1",
        "source":"live Forge dedicated-server RCON",
        "policy":policy,"existing_executor":"SableHauling",
        "completion":True,"observed_flour":True,
        "minecraft_elapsed_ticks":201,"verified_citizen_experience":1,
        "rl_or_adaptation_demonstrated":False,
    }
    def stage(action,flour,experience):
        return {
            "scripted":action,"trained":action,"raw_model":action,
            "disagreement":False,"masked":False,
            "powered":True,"flour":flour,"experience":experience,
        }
    shadow={
        "schema":"hearthbound.live-shadow-evidence.v2",
        "read_only":True,"disagreements":0,"masked":0,
        "learning_improvement_demonstrated":False,
        "stages":{
            "empty_powered":stage("REQUEST_WHEAT_HAUL",0,0),
            "output_ready":stage("COLLECT_OUTPUT",2,0),
            "citizen_experienced":stage("COLLECT_OUTPUT",1,1),
        }
    }
    return trial,shadow

def expect_invalid(trial,shadow):
    try:
        module.build(trial,shadow,restart_verified=True,
                     trial_digest="a"*64,shadow_digest="b"*64)
    except ValueError:
        return
    raise AssertionError("Invalid real evidence was accepted")

def main():
    a,b=sample("TRAINED_MLP")
    event=module.build(a,b,restart_verified=True,trial_digest="a"*64,shadow_digest="b"*64)
    assert event["rewards"]["colony"]["total"]==0.799
    assert event["rewards"]["personal"]["total"]==1
    assert event["limitations"]["offline_reward_label_not_rl_training"] is True
    for policy in ("SCRIPTED","TRAINED_MLP"):
        trial,shadow=sample(policy)
        assert module.build(trial,shadow,restart_verified=True,
                            trial_digest="a"*64,shadow_digest="b"*64)["provenance"]["policy"]==policy
    invalid=[]
    for field,value in (
        ("completion",False),("observed_flour",False),
        ("verified_citizen_experience",0),("minecraft_elapsed_ticks",0),
        ("minecraft_elapsed_ticks",True),("rl_or_adaptation_demonstrated",True),
        ("policy","OTHER"),("existing_executor","Fake")
    ):
        trial,shadow=sample("TRAINED_MLP")
        trial[field]=value
        invalid.append((trial,shadow))
    for stage,field,value in (
        ("empty_powered","experience",1),
        ("empty_powered","flour",1),
        ("empty_powered","raw_model","COLLECT_OUTPUT"),
        ("citizen_experienced","experience",0),
        ("citizen_experienced","flour",0),
        ("output_ready","masked",True)
    ):
        trial,shadow=sample("TRAINED_MLP")
        shadow["stages"][stage][field]=value
        invalid.append((trial,shadow))
    for field,value in (("read_only",False),("disagreements",1),
                        ("learning_improvement_demonstrated",True)):
        trial,shadow=sample("TRAINED_MLP")
        shadow[field]=value
        invalid.append((trial,shadow))
    for trial,shadow in invalid:
        expect_invalid(trial,shadow)
    try:
        module.build(a,b,restart_verified=False,trial_digest="a"*64,shadow_digest="b"*64)
    except ValueError:
        pass
    else:
        raise AssertionError("Missing restart accepted")
    print(f"PASS {4+len(invalid)} real Minecraft reward-contract validation checks")

if __name__=="__main__":
    main()
