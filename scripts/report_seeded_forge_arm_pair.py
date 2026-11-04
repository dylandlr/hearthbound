#!/usr/bin/env python3
"""Verify two policy-arm seeded intervention experiments without reward claims.

Inputs are captured from real Forge CI artifacts. A pair of matching configured
seeds and schedules is a matched control, NOT independent-world evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA="hearthbound.seeded-forge-arm-pair.v1"
WORLD="hearthbound.real-forge-world-provenance.v1"
COVERAGE="hearthbound.forge-intervention-observation-coverage.v1"

def summarize(items):
    if len(items)!=2:
        raise ValueError("exactly two experimental arms required")
    rows=[]
    for world,coverage in items:
        if (world.get("schema")!=WORLD
            or world.get("origin")!="FORGE_SERVER_PROPERTIES_CAPTURE"
            or world.get("fixture_id")!="chest-two-source-seeded-v1"
            or world.get("world_generation_verified") is not False
            or world.get("independent_world_sample_claimed") is not False
            or world.get("neural_policy_executed") is not False
            or world.get("policy_arm") not in ("SCRIPTED","TRAINED_MLP")):
            raise ValueError("invalid configured world provenance")
        if (coverage.get("schema")!=COVERAGE
            or coverage.get("origin")!="REAL_FORGE_RCON_AND_FINALIZED_JOURNAL"
            or coverage.get("configured_world_seed")!=world["world_seed_configured"]
            or coverage.get("explicit_measurement_window") is not True
            or type(coverage.get("measurement_stop_tick"))!=int
            or coverage.get("interventions_verified")!=6
            or coverage.get("counterfactual_outcomes_inferred") is not False
            or coverage.get("learning_or_policy_superiority_claimed") is not False
            or coverage.get("minecraft_actions_authorized") is not False):
            raise ValueError("invalid real intervention/observation evidence")
        digest=coverage.get("sha256")
        body={k:v for k,v in coverage.items() if k!="sha256"}
        canonical=json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False)
        if not isinstance(digest,str) or hashlib.sha256(canonical.encode()).hexdigest()!=digest:
            raise ValueError("tampered observation coverage report")
        count=coverage.get("interventions_with_matching_direct_observation")
        missing=coverage.get("interventions_without_matching_direct_observation")
        if (type(count)!=int or type(missing)!=int or count<0 or missing<0 or
            count+missing!=6 or coverage.get("observational_coverage_rate")!=round(count/6,6)):
            raise ValueError("invalid coverage accounting")
        rows.append({"policy_arm":world["policy_arm"],
                     "run_id":coverage["run_id"],
                     "seed":world["world_seed_configured"],
                     "schedule_sha256":coverage["schedule_sha256"],
                     "observed_matching_interventions":count,
                     "unwitnessed_interventions":missing,
                     "coverage_rate":coverage["observational_coverage_rate"],
                     "journal_sha256":coverage["journal_sha256"]})
    if {x["policy_arm"] for x in rows}!={"SCRIPTED","TRAINED_MLP"}:
        raise ValueError("both scripted and trained-policy arms required")
    if len({x["run_id"] for x in rows})!=2:
        raise ValueError("duplicate captured experiment")
    if len({x["seed"] for x in rows})!=1 or len({x["schedule_sha256"] for x in rows})!=1:
        raise ValueError("different seeded fixtures cannot be compared as paired controls")
    rows.sort(key=lambda x:x["policy_arm"])
    result={"schema":SCHEMA,
            "origin":"REAL_FORGE_MATCHED_SEEDED_FIXTURE",
            "configured_seed":rows[0]["seed"],
            "schedule_sha256":rows[0]["schedule_sha256"],
            "arms":rows,
            "unit_of_analysis":"RUN",
            "independent_world_samples":False,
            "counterfactual_rewards_available":False,
            "policy_superiority_claimed":False,
            "neural_attention_execution_verified":False,
            "interpretation":"Descriptive source-state witness coverage, not measured model advantage"}
    result["sha256"]=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("scripted_world",type=Path)
    p.add_argument("scripted_coverage",type=Path)
    p.add_argument("trained_world",type=Path)
    p.add_argument("trained_coverage",type=Path)
    p.add_argument("--output",type=Path,default=Path("verified-seeded-forge-arm-pair.json"))
    args=p.parse_args()
    pairs=[(json.loads(args.scripted_world.read_text()),json.loads(args.scripted_coverage.read_text())),
           (json.loads(args.trained_world.read_text()),json.loads(args.trained_coverage.read_text()))]
    result=summarize(pairs)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("REAL_FORGE_SEEDED_ARMS_VERIFIED seed="+result["configured_seed"]+
          " matched_controls=true independence_unverified=true")

if __name__=="__main__":
    main()
