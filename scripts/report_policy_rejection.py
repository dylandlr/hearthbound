#!/usr/bin/env python3
"""Report an observed server-side refusal, not an RL transition.

A preflight refusal with no dispatch receives zero personal/colony task credit.
"""
import argparse
import json
import re
from pathlib import Path

REJECT = re.compile(
    r"^REAL_POLICY_TRIAL_REJECTION mode=(SCRIPTED|TRAINED_MLP)"
    r" reason=SOURCE_NO_WHEAT dispatched=false"
    r" credit=0 existing_job_unchanged=true$"
)

def parse(log, expected_mode):
    matches=[REJECT.fullmatch(line.strip()) for line in log.splitlines()
             if "REAL_POLICY_TRIAL_REJECTION" in line]
    if len(matches)!=1 or matches[0] is None:
        raise ValueError("Require exactly one audited Minecraft source-shortage refusal")
    mode=matches[0].group(1)
    if mode!=expected_mode:
        raise ValueError("Refusal belongs to wrong policy arm")
    if "real source shortage rejection: Source inventory has no real wheat" not in log:
        raise ValueError("Missing actual Minecraft command refusal")
    if "no new hauling job after shortage: " not in log or "status=Haul complete" not in log:
        raise ValueError("Missing independent unchanged-job audit")
    if log.count("REAL_POLICY_SELECTED_SABLE_HAUL mode="+mode)!=1:
        raise ValueError("Restored-source trial did not issue exactly one valid assignment")
    return {
        "schema":"hearthbound.minecraft-rejected-attempt.v1",
        "origin":"dedicated Forge/Create server RCON observation",
        "policy":mode,
        "reason":"SOURCE_NO_WHEAT",
        "task_dispatched":False,
        "prior_job_unchanged":True,
        "personal_task_reward":0.0,
        "colony_task_reward":0.0,
        "training_transition":False,
        "limitation":"Missing source inventory in current five-feature neural input; refusal is enforced by authoritative task gate"
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("rcon_log",type=Path)
    p.add_argument("--expected-mode",required=True,choices=["SCRIPTED","TRAINED_MLP"])
    p.add_argument("--output",type=Path,default=Path("policy-rejection.json"))
    args=p.parse_args()
    report=parse(args.rcon_log.read_text(errors="replace"),args.expected_mode)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("VERIFIED_MINECRAFT_POLICY_REJECTION",json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
