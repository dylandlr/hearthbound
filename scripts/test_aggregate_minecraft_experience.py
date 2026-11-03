#!/usr/bin/env python3
"""Pure synthetic validation: not real Minecraft training evidence."""
import importlib.util
from pathlib import Path

def load(name):
    path=Path(__file__).with_name(name+".py")
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

experience=load("build_minecraft_experience")
aggregate=load("aggregate_minecraft_experience")
test=load("test_build_minecraft_experience")

def main():
    rows=[]
    for mode in ("SCRIPTED","TRAINED_MLP"):
        trial,shadow=test.sample(mode)
        rows.append(experience.build(trial,shadow,restart_verified=True,
                                     trial_digest="a"*64,shadow_digest="b"*64))
    data=aggregate.aggregate(*rows)
    assert len(data["transitions"])==2 and data["training_performed"] is False
    invalid={**rows[1],"selected_action":"COLLECT_OUTPUT"}
    try:
        aggregate.aggregate(rows[0],invalid)
    except ValueError:pass
    else:raise AssertionError("Unverified action was accepted")
    invalid={**rows[1],"provenance":{**rows[1]["provenance"],"world_seed":"other"}}
    try:
        aggregate.aggregate(rows[0],invalid)
    except ValueError:pass
    else:raise AssertionError("Unmatched seed was accepted")
    print("PASS 3 reward dataset aggregation checks")

if __name__=="__main__":main()
