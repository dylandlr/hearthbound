#!/usr/bin/env python3
"""Synthetic smoke fixture for standalone Java shadow CLI.

NO Minecraft server is involved. The real workflow uses archived RCON logs.
"""
import argparse
from pathlib import Path

VECTORS={
    "empty":"1,0,0,0,0,0,1,0,0,0",
    "unknown":"1,0,0,0,0,1,0,0,0,0",
    "available":"1,0,0,0,0,0,0,1,0,0",
}
ACTIONS={
    "empty":"WAIT_FOR_SUPPLY",
    "unknown":"INSPECT_SOURCE",
    "available":"REQUEST_WHEAT_HAUL",
}
def make():
    lines=[]
    for stage in ("empty","unknown","available"):
        state=stage.upper()
        action=ACTIONS[stage]
        lines.append(f"REAL_OBSERVATION_V2 stage={stage} "
                     f"schema=hearthbound.mill-observation.v2 tensor={VECTORS[stage]}")
        lines.append(f"REAL_SOURCE_PLAN stage={stage} action={action} "
                     f"source={state} read_only=true")
    return "\n".join(lines)+"\n"
def main():
    p=argparse.ArgumentParser()
    p.add_argument("path",type=Path)
    a=p.parse_args()
    a.path.write_text(make())
    print("SYNTHETIC_SHADOW_FIXTURE_WRITTEN not_minecraft_evidence=true")
if __name__=="__main__":
    main()
