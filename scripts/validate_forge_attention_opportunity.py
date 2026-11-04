#!/usr/bin/env python3
"""Validate a real Forge pre-inspection opportunity, never inventory truth."""
import argparse
import json
import re
from pathlib import Path

PREFIX="ATTENTION_OPPORTUNITY "
SCHEMA="hearthbound.forge-attention-opportunity.v1"
UUID=re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
POS=re.compile(r"^-?\d+,-?\d+,-?\d+$")
DIM=re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")

def parse(line):
    if not line.startswith(PREFIX):
        raise ValueError("not an opportunity")
    fields={}
    for term in line[len(PREFIX):].strip().split():
        if term.count("=")!=1:
            raise ValueError("invalid field")
        key,value=term.split("=",1)
        if key in fields:
            raise ValueError("duplicate field")
        fields[key]=value
    expected={"schema","tick","observer","dimension","candidates",
              "candidate_count","selected","budget","policy",
              "inventory_read","action_authorized"}
    if set(fields)!=expected:
        raise ValueError("missing, unknown, or leaked opportunity field")
    if (fields["schema"]!=SCHEMA or fields["inventory_read"]!="false"
            or fields["action_authorized"]!="false"):
        raise ValueError("invalid evidence boundary")
    if not UUID.fullmatch(fields["observer"]) or not DIM.fullmatch(fields["dimension"]):
        raise ValueError("invalid observer or dimension")
    if not fields["tick"].isdigit() or fields["policy"] not in ("LEAST_RECENTLY_SAMPLED","NEURAL_CAUSAL_MLP_OPT_IN"):
        raise ValueError("invalid time or policy")
    if fields["budget"]!="1" or not fields["candidate_count"].isdigit():
        raise ValueError("invalid budget or candidate count")
    candidates=fields["candidates"].split(";")
    if not 1<=len(candidates)<=4 or len(candidates)!=int(fields["candidate_count"]):
        raise ValueError("unbounded or inconsistent candidate set")
    if any(not POS.fullmatch(pos) for pos in candidates) or len(set(candidates))!=len(candidates):
        raise ValueError("invalid or duplicate candidates")
    if not POS.fullmatch(fields["selected"]) or fields["selected"] not in candidates:
        raise ValueError("selected source not in registered candidate set")
    return {"schema":SCHEMA,"tick":int(fields["tick"]),
            "observer":fields["observer"],"dimension":fields["dimension"],
            "candidates":candidates,"selected":fields["selected"],
            "policy":fields["policy"],
            "budget":1,"inventory_read":False,"action_authorized":False,
            "counterfactual_outcomes_available":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("source",type=Path)
    parser.add_argument("--output",type=Path,default=Path("real-attention-opportunity.json"))
    args=parser.parse_args()
    records=[parse(x) for x in args.source.read_text().splitlines() if x.strip()]
    if len(records)!=1:
        raise ValueError("expected precisely one operator-captured opportunity")
    report={"schema":"hearthbound.verified-forge-attention-opportunity.v1",
            "origin":"REAL_FORGE_RCON","records":records,
            "minecraft_actions_authorized":False,"counterfactual_rewards_inferred":False}
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("VERIFIED_REAL_FORGE_ATTENTION_OPPORTUNITY source=RCON records=1")

if __name__=="__main__":
    main()
