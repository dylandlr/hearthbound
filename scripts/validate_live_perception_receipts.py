#!/usr/bin/env python3
"""Validate captured *real* Forge source receipts without inventing gameplay.

Use on output from /hearthbound perception_receipts or server logs. This
validator does not generate Minecraft events, camera frames, or simulated claims.
"""
import argparse
import json
import re
from pathlib import Path

SCHEMA="hearthbound.live-perception-receipt.v1"
PREFIX="PERCEPTION_RECEIPT "
DIMS=re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")
POS=re.compile(r"^-?\d+, ?-?\d+, ?-?\d+$")
UUID=re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

def parse(line):
    i=line.find(PREFIX)
    if i<0:return None
    fields={}
    for token in line[i+len(PREFIX):].strip().split():
        if "=" not in token:
            continue
        key,value=token.split("=",1)
        if key in fields:
            raise ValueError("Duplicate receipt key")
        fields[key]=value
    required={"schema","dimension","source","revision","tick","state",
              "wheat","observer","evidence","action_authorized"}
    if set(fields)!=required:
        raise ValueError("Receipt has missing or unknown fields")
    if fields["schema"]!=SCHEMA or fields["evidence"]!="REAL_FORGE_SOURCE_OBSERVATION":
        raise ValueError("Wrong receipt provenance")
    if fields["action_authorized"]!="false":
        raise ValueError("Receipt may never confer action authorization")
    if not DIMS.fullmatch(fields["dimension"]) or not POS.fullmatch(fields["source"]):
        raise ValueError("Invalid dimension or source location")
    if not UUID.fullmatch(fields["observer"]):
        raise ValueError("Invalid observer UUID")
    if not fields["revision"].isdigit() or not fields["tick"].isdigit() or not fields["wheat"].isdigit():
        raise ValueError("Invalid revision/tick/wheat")
    fields["revision"]=int(fields["revision"])
    fields["tick"]=int(fields["tick"])
    fields["wheat"]=int(fields["wheat"])
    if fields["revision"]<1 or fields["tick"]<0:
        raise ValueError("Impossible revision or tick")
    if fields["state"] not in ("EMPTY","AVAILABLE"):
        raise ValueError("Unknown state must never be treated as an observed inventory")
    if (fields["state"]=="EMPTY" and fields["wheat"]!=0 or
        fields["state"]=="AVAILABLE" and fields["wheat"]<=0):
        raise ValueError("Source state inconsistent with measured wheat")
    return fields

def validate_lines(lines):
    last={}
    accepted=[]
    for line in lines:
        receipt=parse(line)
        if receipt is None:continue
        key=receipt["dimension"],receipt["source"]
        previous=last.get(key)
        if previous and (receipt["revision"]!=previous["revision"]+1 or
                         receipt["tick"]<previous["tick"]):
            raise ValueError("Nonmonotonic source receipt; missing log or changed session")
        last[key]=receipt
        accepted.append(receipt)
    return {"schema":"hearthbound.live-perception-replay-validation.v1",
            "receipts":len(accepted),"distinct_sources":len(last),
            "minecraft_events_validated":len(accepted),
            "task_execution_authorized":False,
            "events":accepted}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=validate_lines(args.input.read_text().splitlines())
    data=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.output:args.output.write_text(data)
    else:print(data,end="")
if __name__=="__main__":main()
