#!/usr/bin/env python3
"""Report one authenticated Minecraft RCON trial. Never infer success from CI exit status."""
import argparse
import json
from pathlib import Path
import re

RESULT=re.compile(r"REAL_POLICY_TRIAL_RESULT\s+mode=(SCRIPTED|TRAINED_MLP)\s+completion=(\d+)\s+elapsed_ticks=(\d+)\s+verified_experience=(\d+)\s+flour_observed=(\d+)\s+executor=(\w+)")

def parse(log, expected):
    matches=list(RESULT.finditer(log))
    if len(matches)!=1:
        raise ValueError(f"Require exactly one real policy trial result; found {len(matches)}")
    mode,completion,ticks,experience,flour,executor=matches[0].groups()
    if mode!=expected or executor!="SableHauling":
        raise ValueError("Wrong policy or executor in authenticated result")
    if completion!="1" or experience!="1" or flour!="1":
        raise ValueError("Real Minecraft task outcome not verified")
    elapsed=int(ticks)
    if elapsed<1 or elapsed>20000:
        raise ValueError("Trial game tick duration outside expected bounds")
    # The source is the real Forge RCON experiment output, not model training data.
    required=("REAL_CITIZEN_EXPERIENCE_OBSERVED",
              "REAL_CREATE_FLOUR_OBSERVED",
              "SABLE_VERIFIED_EXPERIENCE_SURVIVED_REAL_SERVER_RESTART")
    # Restart proof comes from separate RCON restart script, not in smoke-rcon.log.
    for marker in required[:2]:
        if marker not in log:
            raise ValueError("Missing independent evidence: "+marker)
    if f"REAL_POLICY_SELECTED_SABLE_HAUL mode={mode}" not in log:
        raise ValueError("Missing explicit model/scripted assignment provenance")
    return {"schema":"hearthbound.real-minecraft-policy-trial.v1",
            "policy":mode,"source":"live Forge dedicated-server RCON",
            "completion":True,"minecraft_elapsed_ticks":elapsed,
            "observed_flour":True,"verified_citizen_experience":1,
            "existing_executor":"SableHauling",
            "comparative_advantage_demonstrated":False,
            "rl_or_adaptation_demonstrated":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("rcon_log",type=Path)
    p.add_argument("--expected-mode",required=True,choices=["SCRIPTED","TRAINED_MLP"])
    p.add_argument("--output",type=Path,default=Path("policy-trial-result.json"))
    a=p.parse_args()
    result=parse(a.rcon_log.read_text(errors="replace"),a.expected_mode)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print("VERIFIED_REAL_POLICY_TRIAL",json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
