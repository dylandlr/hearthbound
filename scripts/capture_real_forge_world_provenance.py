#!/usr/bin/env python3
"""Validate and persist experimental seed/fixture identity for real Forge CI.

This metadata records the configured server seed, NOT a claim that it is
independent of other runs or a proof of generated terrain diversity.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA="hearthbound.real-forge-world-provenance.v1"
POLICIES={"SCRIPTED","TRAINED_MLP"}
REQUIRED=("level-seed","level-name","online-mode","enable-rcon")

def parse_properties(contents):
    result={}
    for raw in contents.splitlines():
        stripped=raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:raise ValueError("malformed property")
        k,v=stripped.split("=",1)
        if k in result:raise ValueError("duplicate server property: "+k)
        result[k]=v
    return result

def provenance(contents,policy,fixture,expected_seed=None):
    if policy not in POLICIES:raise ValueError("unsupported trial arm")
    if not re.fullmatch("[a-zA-Z0-9_.-]{1,100}",fixture):
        raise ValueError("invalid fixture identifier")
    props=parse_properties(contents)
    if any(not props.get(k) for k in REQUIRED):
        raise ValueError("required world properties missing")
    seed=props["level-seed"]
    if expected_seed is not None and seed!=expected_seed:
        raise ValueError("configured seed mismatch")
    if not 1<=len(seed)<=128 or any(c in seed for c in "\n\r\x00"):
        raise ValueError("invalid seed")
    if props["online-mode"]!="false" or props["enable-rcon"]!="true":
        raise ValueError("unexpected disposable acceptance server configuration")
    digest=hashlib.sha256(contents.encode()).hexdigest()
    return {
        "schema":SCHEMA,
        "origin":"FORGE_SERVER_PROPERTIES_CAPTURE",
        "world_seed_configured":seed,
        "world_name":props["level-name"],
        "fixture_id":fixture,
        "policy_arm":policy,
        "server_properties_sha256":digest,
        "world_generation_verified":False,
        "independent_world_sample_claimed":False,
        "neural_policy_executed":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("properties",type=Path)
    p.add_argument("--policy",required=True,choices=sorted(POLICIES))
    p.add_argument("--fixture",required=True)
    p.add_argument("--expected-seed",required=True)
    p.add_argument("--output",type=Path,default=Path("real-world-provenance.json"))
    args=p.parse_args()
    value=provenance(args.properties.read_text(),args.policy,args.fixture,args.expected_seed)
    args.output.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
    print("FORGE_WORLD_PROVENANCE_CAPTURED seed="+value["world_seed_configured"]
          +" fixture="+value["fixture_id"]+" policy="+value["policy_arm"])

if __name__=="__main__":
    main()
