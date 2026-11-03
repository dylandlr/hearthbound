#!/usr/bin/env python3
"""Validate three read-only observations captured from an actual Minecraft server."""
import argparse
import json
import re
from pathlib import Path

MARKER=re.compile(r"^REAL_SOURCE_OBSERVATION stage=(empty|unknown|available) state=(EMPTY|UNKNOWN|AVAILABLE) wheat=(\d+)$")
EXPECTED={"empty":("EMPTY",0),"unknown":("UNKNOWN",0),"available":("AVAILABLE",1)}

def parse(log):
    found={}
    for line in log.splitlines():
        if "REAL_SOURCE_OBSERVATION" not in line:
            continue
        match=MARKER.fullmatch(line.strip())
        if match is None:
            raise ValueError("Malformed source observation evidence")
        stage,state,number=match.groups()
        if stage in found or (state,int(number))!=EXPECTED[stage]:
            raise ValueError("Duplicate or contradictory source observation")
        found[stage]={"state":state,"wheat":int(number)}
    if set(found)!=set(EXPECTED):
        raise ValueError("Missing source-observation stages")
    for reason in ("real partial observation of empty source: SOURCE_OBSERVATION state=EMPTY wheat=0",
                   "real partial observation of unsupported source: SOURCE_OBSERVATION state=UNKNOWN wheat=0 reason=NO_BLOCK_ENTITY",
                   "real partial observation after restoring wheat: SOURCE_OBSERVATION state=AVAILABLE wheat=1"):
        if reason not in log:
            raise ValueError("Missing actual server evidence: "+reason)
    return {
        "schema":"hearthbound.real-source-observation.v1",
        "source":"Forge Minecraft RCON, read-only server observations",
        "stages":found,
        "neural_model_updated":False,
        "learning_demonstrated":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("log",type=Path)
    p.add_argument("--output",type=Path,default=Path("source-observations.json"))
    a=p.parse_args()
    record=parse(a.log.read_text(errors="replace"))
    a.output.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print("VERIFIED_REAL_SOURCE_OBSERVATIONS",json.dumps(record,sort_keys=True))

if __name__=="__main__":
    main()
