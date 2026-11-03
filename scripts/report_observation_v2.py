#!/usr/bin/env python3
"""Audit exact ten-feature tensors emitted by the real Minecraft source probe."""
import argparse
import json
import math
import re
from pathlib import Path

FEATURES=[
    "powered","mill_wheat_present","mill_flour_present","mill_blocked",
    "verified_experience_norm","source_unknown","source_empty",
    "source_available","task_active","source_stale"
]
EXPECTED={
    "unknown":[1.0,0.0,0.0],
    "empty":[0.0,1.0,0.0],
    "available":[0.0,0.0,1.0]
}
PATTERN=re.compile(r"^REAL_OBSERVATION_V2 stage=(unknown|empty|available) schema=hearthbound\.mill-observation\.v2 tensor=([0-9.,]+)$")
def analyze(source):
    stages={}
    for line in source.splitlines():
        if "REAL_OBSERVATION_V2" not in line:continue
        match=PATTERN.fullmatch(line.strip())
        if match is None:raise ValueError("Malformed real Minecraft v2 observation")
        stage,csv=match.groups()
        if stage in stages:raise ValueError("Duplicate Minecraft observation")
        try:tensor=[float(n) for n in csv.split(",")]
        except ValueError as exc:raise ValueError("Invalid tensor number") from exc
        if len(tensor)!=10 or any(not math.isfinite(n) or n<0 or n>1 for n in tensor):
            raise ValueError("Bad v2 tensor dimensions or values")
        if tensor[5:8]!=EXPECTED[stage] or tensor[9]!=0.0:
            raise ValueError("Unknown/empty/available masking incorrect")
        if tensor[0]!=1.0 or tensor[1]!=0.0 or tensor[2]!=0.0 or tensor[8]!=0.0:
            raise ValueError("Not an idle powered mill observation")
        stages[stage]=tensor
    if set(stages)!=set(EXPECTED):
        raise ValueError("Incomplete real-world source observations")
    return {
        "schema":"hearthbound.live-observation-tensor.v2",
        "feature_names":FEATURES,"width":10,
        "source":"read-only Forge/Create Minecraft RCON",
        "training_performed":False,
        "stages":stages
    }
def main():
    p=argparse.ArgumentParser()
    p.add_argument("log",type=Path)
    p.add_argument("--output",type=Path,default=Path("observation-v2.json"))
    a=p.parse_args()
    result=analyze(a.log.read_text(errors="replace"))
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("VERIFIED_MINECRAFT_OBSERVATION_V2",json.dumps(result,sort_keys=True))
if __name__=="__main__":
    main()
