#!/usr/bin/env python3
"""Pure parser tests; synthetic fixtures are NOT Minecraft outcome evidence."""
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("comparison",Path(__file__).with_name("compare_real_policy_trials.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def fixture(mode,ticks):
    return {
        "schema":"hearthbound.real-minecraft-policy-trial.v1",
        "policy":mode,
        "source":"live Forge dedicated-server RCON",
        "completion":True,
        "minecraft_elapsed_ticks":ticks,
        "observed_flour":True,
        "verified_citizen_experience":1,
        "existing_executor":"SableHauling",
        "comparative_advantage_demonstrated":False,
        "rl_or_adaptation_demonstrated":False,
    }
def check():
    a=fixture("SCRIPTED",145)
    b=fixture("TRAINED_MLP",162)
    report=module.compare(a,b)
    assert report["trained_minus_scripted_ticks"]==17
    assert not report["policy_superiority_claimed"]
    assert report["episodes_per_arm"]==1
    invalid=[
        ({"schema":"invalid",**{k:v for k,v in a.items() if k!="schema"}},b),
        (b,a),
        ({**a,"completion":False},b),
        (a,{**b,"minecraft_elapsed_ticks":0}),
        (a,{**b,"minecraft_elapsed_ticks":True}),
        (a,{**b,"observed_flour":False}),
        (a,{**b,"verified_citizen_experience":0}),
        (a,{**b,"existing_executor":"Fake"}),
        (a,{**b,"policy_superiority_claimed":True,"comparative_advantage_demonstrated":True}),
        (a,{**b,"rl_or_adaptation_demonstrated":True})
    ]
    for candidate in invalid:
        try:
            module.compare(*candidate)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid policy comparison accepted")
    print("PASS 11 dual-policy result validation checks")

if __name__=="__main__":
    check()
