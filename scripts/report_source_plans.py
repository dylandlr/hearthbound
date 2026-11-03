#!/usr/bin/env python3
"""Audit read-only Minecraft source-aware planner decisions, not trained policy."""
import argparse
import json
import re
from pathlib import Path

EXPECTED={
    "empty":("WAIT_FOR_SUPPLY","EMPTY"),
    "unknown":("INSPECT_SOURCE","UNKNOWN"),
    "available":("REQUEST_WHEAT_HAUL","AVAILABLE"),
}
PATTERN=re.compile(r"REAL_SOURCE_PLAN stage=(\w+) action=(\w+) source=(\w+) read_only=true")

def parse(log):
    found={}
    for line in log.splitlines():
        if "REAL_SOURCE_PLAN" not in line:continue
        match=PATTERN.fullmatch(line.strip())
        if match is None:raise ValueError("Malformed or truncated source plan receipt")
        stage,action,source=match.groups()
        if stage not in EXPECTED or stage in found or (action,source)!=EXPECTED[stage]:
            raise ValueError("Unexpected source planning decision")
        label={
          "empty":"live source-aware empty planner",
          "unknown":"live source-aware unknown planner",
          "available":"live source-aware available planner",
        }[stage]
        if not any(line.startswith(label+": SOURCE_PLAN ") and
                   "source="+source in line and "action="+action in line and
                   "EXECUTION_DISABLED" in line and "ML_MODEL_UNCHANGED" in line
                   for line in log.splitlines()):
            raise ValueError("No authentic read-only Minecraft planner observation for "+stage)
        found[stage]={"source":source,"action":action}
    if set(found)!=set(EXPECTED):
        raise ValueError("Missing real Minecraft planning stages")
    return {
        "schema":"hearthbound.live-source-planner.v1",
        "source":"actual Forge/Create server RCON",
        "stages":found,
        "executed":False,
        "trained_policy_updated":False,
        "conclusion":"partial-observation reference planning only"
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("log",type=Path)
    p.add_argument("--output",type=Path,default=Path("source-plans.json"))
    a=p.parse_args()
    result=parse(a.log.read_text(errors="replace"))
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("VERIFIED_SOURCE_PLANNER",json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
