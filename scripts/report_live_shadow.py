#!/usr/bin/env python3
"""Validate compact paired policy decisions logged by a real Forge RCON test.

The smoke client compares full untruncated server responses *before* emitting
compact pairs. This parser rejects missing/duplicate states and unsafe results.
"""
import argparse
import json
import pathlib
import re

REQUIRED={
    "empty_powered":"REQUEST_WHEAT_HAUL",
    "output_ready":"COLLECT_OUTPUT",
    "citizen_experienced":"COLLECT_OUTPUT",
}
PAIR=re.compile(
    r"LIVE_SHADOW_PAIR stage=(\w+) expected=(\w+) scripted=(\w+) trained=(\w+)"
    r" raw_mlp=(\w+) citizen=([a-f0-9-]+) powered=(true|false)"
    r" wheat=(\d+) flour=(\d+) blocked=(true|false) experience=(\d+)"
    r" disagreement=(true|false) masked=(true|false) read_only=true"
)
def analyze(text):
    found={}
    citizen_id=None
    for line in text.splitlines():
        if "LIVE_SHADOW_PAIR" not in line:
            continue
        match=PAIR.search(line)
        if not match:
            raise ValueError("Malformed or truncated LIVE_SHADOW_PAIR evidence")
        (stage,expected,scripted,trained,raw,citizen,powered,wheat,flour,blocked,
         experience,disagreement,masked)=match.groups()
        if stage not in REQUIRED or stage in found:
            raise ValueError("Unexpected or repeated shadow stage "+stage)
        if expected!=REQUIRED[stage] or scripted!=expected or trained!=expected:
            raise ValueError("Policy output disagreement with expected state "+stage)
        if raw!=trained or disagreement!="false" or masked!="false":
            raise ValueError("Unexpected model divergence or masking in controlled fixture")
        if citizen_id is None:
            citizen_id=citizen
        elif citizen_id!=citizen:
            raise ValueError("Shadow states reference different citizens")
        if powered!="true":
            raise ValueError("Expected powered Create millstone in "+stage)
        if stage=="empty_powered" and (wheat!="0" or flour!="0" or blocked!="false" or experience!="0"):
            raise ValueError("Unclean starting fixture")
        if stage in ("output_ready","citizen_experienced") and int(flour)<1:
            raise ValueError("No physical flour seen in "+stage)
        if stage=="citizen_experienced" and experience!="1":
            raise ValueError("Verified experience absent")
        found[stage]={
            "scripted":scripted,"trained":trained,"raw_model":raw,
            "disagreement":False,"masked":False,
            "experience":int(experience),"powered":True,
            "flour":int(flour),
        }
    missing=set(REQUIRED)-set(found)
    if missing:
        raise ValueError("Missing real Minecraft shadow states: "+", ".join(sorted(missing)))
    return {
        "schema":"hearthbound.live-shadow-evidence.v2",
        "source":"validated full RCON responses via compact Forge smoke transcript",
        "read_only":True,"citizen":citizen_id,
        "stages":found,"disagreements":0,"masked":0,
        "learning_improvement_demonstrated":False,
    }
def main():
    p=argparse.ArgumentParser()
    p.add_argument("log",type=pathlib.Path)
    p.add_argument("--output",type=pathlib.Path,default=pathlib.Path("live-shadow-report.json"))
    args=p.parse_args()
    result=analyze(args.log.read_text(encoding="utf-8",errors="replace"))
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
