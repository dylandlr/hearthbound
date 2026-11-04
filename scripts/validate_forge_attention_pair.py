#!/usr/bin/env python3
"""Pair actual Forge pre-inspection choices with their selected-source outcomes."""
import argparse
import json
import re
from pathlib import Path
from validate_forge_attention_opportunity import parse as parse_choice

SCHEMA="hearthbound.forge-attention-outcome.v1"
UUID=re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
POS=re.compile(r"^-?\d+,-?\d+,-?\d+$")

def parse_outcome(line):
    if not line.startswith("ATTENTION_OUTCOME "):
        raise ValueError("not an outcome record")
    fields={}
    for token in line[len("ATTENTION_OUTCOME "):].split():
        if token.count("=")!=1:
            raise ValueError("malformed outcome")
        key,value=token.split("=",1)
        if key in fields: raise ValueError("duplicate outcome key")
        fields[key]=value
    required={"schema","tick","observer","dimension","selected","status",
              "reason","state","wheat","evidence","action_authorized"}
    if set(fields)!=required or fields["schema"]!=SCHEMA:
        raise ValueError("invalid outcome schema")
    if (fields["action_authorized"]!="false" or not fields["tick"].isdigit()
        or not UUID.fullmatch(fields["observer"]) or not POS.fullmatch(fields["selected"])):
        raise ValueError("invalid outcome identity")
    if fields["status"]=="OBSERVED":
        if fields["reason"]!="VERIFIED" or fields["evidence"]!="REAL_FORGE_SOURCE_OBSERVATION":
            raise ValueError("unverified observation")
        if fields["state"] not in ("AVAILABLE","EMPTY") or not fields["wheat"].isdigit():
            raise ValueError("invalid observed quantity")
        if (fields["state"]=="EMPTY")!=(int(fields["wheat"])==0):
            raise ValueError("inconsistent observed state")
        wheat=int(fields["wheat"])
    elif fields["status"]=="UNOBSERVED":
        if (fields["reason"] not in ("CHUNK_UNLOADED","OBSERVER_UNAVAILABLE","SENSOR_UNKNOWN")
            or fields["state"]!="UNKNOWN" or fields["wheat"]!="-1"
            or fields["evidence"]!="NO_VALID_OBSERVATION"):
            raise ValueError("unobserved outcome contains source truth")
        wheat=None
    else:
        raise ValueError("invalid outcome status")
    return dict(tick=int(fields["tick"]),observer=fields["observer"],
                dimension=fields["dimension"],selected=fields["selected"],
                status=fields["status"],reason=fields["reason"],
                state=fields["state"] if wheat is not None else None,
                wheat=wheat)

def pair(choice_line,outcome_line):
    choice=parse_choice(choice_line)
    outcome=parse_outcome(outcome_line)
    for field in ("tick","observer","dimension","selected"):
        if choice[field]!=outcome[field]:
            raise ValueError("unmatched citizen attention attempt: "+field)
    return {"schema":"hearthbound.forge-attention-paired-evidence.v1",
            "origin":"REAL_FORGE_RCON",
            "opportunity":choice,"outcome":outcome,
            "unselected_candidate_outcomes":"UNKNOWN",
            "counterfactual_reward_available":False,
            "training_performed":False,
            "minecraft_actions_authorized":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("choice",type=Path)
    p.add_argument("outcome",type=Path)
    p.add_argument("--output",type=Path,default=Path("real-attention-paired-evidence.json"))
    args=p.parse_args()
    opportunities=[x for x in args.choice.read_text().splitlines() if x.strip()]
    outcomes=[x for x in args.outcome.read_text().splitlines() if x.strip()]
    if len(opportunities)!=1 or len(outcomes)!=1:
        raise ValueError("one choice and one corresponding outcome required")
    report=pair(opportunities[0],outcomes[0])
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("REAL_FORGE_ATTENTION_PAIR_VALIDATED outcome="+report["outcome"]["status"]
          +" unselected=UNKNOWN execution=false")

if __name__=="__main__":
    main()
