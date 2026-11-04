#!/usr/bin/env python3
"""Check whether a collection of real Forge runs actually varies by world seed."""
import argparse
import json
from pathlib import Path
from capture_real_forge_world_provenance import SCHEMA, POLICIES

def cohort(paths):
    if len(paths)<2:raise ValueError("at least two run arms required")
    entries=[]
    seen=set()
    for path in paths:
        row=json.loads(Path(path).read_text())
        if not isinstance(row,dict) or set(row)!={
            "schema","origin","world_seed_configured","world_name","fixture_id",
            "policy_arm","server_properties_sha256","world_generation_verified",
            "independent_world_sample_claimed","neural_policy_executed"}:
            raise ValueError("unexpected provenance fields")
        if (row["schema"]!=SCHEMA or row["origin"]!="FORGE_SERVER_PROPERTIES_CAPTURE"
            or row["policy_arm"] not in POLICIES or not row["world_seed_configured"]
            or row["world_generation_verified"] is not False
            or row["independent_world_sample_claimed"] is not False
            or row["neural_policy_executed"] is not False):
            raise ValueError("untrusted world provenance")
        identity=(row["world_seed_configured"],row["fixture_id"],row["policy_arm"])
        if identity in seen:raise ValueError("duplicate world/fixture/policy arm")
        seen.add(identity)
        entries.append(row)
    seeds={x["world_seed_configured"] for x in entries}
    fixtures={x["fixture_id"] for x in entries}
    # Even distinct seeds don't prove different actual environment conditions.
    return {
        "schema":"hearthbound.real-forge-cohort-provenance.v1",
        "origin":"FORGE_SERVER_PROPERTIES_CAPTURE",
        "runs":len(entries),
        "configured_distinct_seeds":len(seeds),
        "configured_distinct_fixtures":len(fixtures),
        "shared_seed_control_only":len(seeds)==1,
        "independent_world_conditions_verified":False,
        "generalization_claim_allowed":False,
        "minecraft_actions_authorized":False,
        "arms":[{"seed":x["world_seed_configured"],
                 "fixture_id":x["fixture_id"],
                 "policy_arm":x["policy_arm"]} for x in sorted(entries,key=lambda e:(e["world_seed_configured"],e["policy_arm"]))]
    }

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("reports",nargs="+",type=Path)
    cli.add_argument("--output",type=Path,default=Path("real-forge-cohort-provenance.json"))
    args=cli.parse_args()
    result=cohort(args.reports)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("FORGE_COHORT_PROVENANCE configured_distinct_seeds="+str(result["configured_distinct_seeds"])
          +" independent_conditions_verified=false")

if __name__=="__main__":
    main()
