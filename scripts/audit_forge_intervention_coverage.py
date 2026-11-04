#!/usr/bin/env python3
"""Audit witnessed Forge source states after controlled resource interventions.

Counts only directly observed *selected-source* readings inside conservative
post-intervention windows. It never labels unseen changes as perceived and
never assigns rewards to unselected sources.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from real_forge_resource_schedule import validate_log
from validate_forge_attention_manifest import verify as verify_manifest
from validate_forge_attention_pair import pair

SCHEMA="hearthbound.forge-intervention-observation-coverage.v1"

def matched_events(journal):
    previous=-1
    for row in journal:
        raw=base64.urlsafe_b64decode(row["payload_b64"]+"="*((-len(row["payload_b64"]))%4)).decode()
        parts=raw.split("\n")
        if len(parts)!=2:raise ValueError("invalid journal pair")
        event=pair(*parts)
        choice=event["opportunity"]
        outcome=event["outcome"]
        if choice["tick"]<previous:raise ValueError("non-chronological journal")
        previous=choice["tick"]
        yield {"tick":choice["tick"],
               "source":choice["selected"].replace(","," "),
               "observer":choice["observer"],
               "status":outcome["status"],
               "wheat":outcome["wheat"]}

def audit(schedule, journal_path, manifest_path, world=None):
    validated=validate_log(schedule)
    finalized=verify_manifest(Path(journal_path),Path(manifest_path),minimum=1)
    if world is not None:
        if (world.get("schema")!="hearthbound.real-forge-world-provenance.v1"
            or world.get("origin")!="FORGE_SERVER_PROPERTIES_CAPTURE"
            or world.get("world_seed_configured")!=schedule["configured_world_seed"]
            or world.get("fixture_id")!="chest-two-source-seeded-v1"
            or world.get("world_generation_verified") is not False):
            raise ValueError("world configuration disagrees with resource schedule")
    rows=[json.loads(line) for line in Path(journal_path).read_text().splitlines()]
    observations=list(matched_events(rows))
    interventions=schedule["executions"]
    end=max(x["tick_after"] for x in interventions)
    results=[]
    for i,event in enumerate(interventions):
        # Same-source mutations supersede one another. Evidence exactly at
        # mutation tick is excluded because RCON and sampler ordering within
        # that Minecraft tick is not proven.
        future=[x["tick_before"] for x in interventions[i+1:]
                if x["source"]==event["source"]]
        until=min(future) if future else end+1
        eligible=[o for o in observations if
                  o["source"]==event["source"] and
                  event["tick_after"]<o["tick"]<until and
                  o["status"]=="OBSERVED"]
        consistent=[o for o in eligible if o["wheat"]==event["wheat"]]
        contradictory=[o for o in eligible if o["wheat"]!=event["wheat"]]
        results.append({
            "intervention_index":event["index"],
            "source":event["source"],
            "wheat_after_operator_mutation":event["wheat"],
            "mutation_tick_after":event["tick_after"],
            "window_end_exclusive":until,
            "direct_selected_observations_in_window":len(eligible),
            "observations_matching_expected_wheat":len(consistent),
            "observations_not_matching_expected_wheat":len(contradictory),
            "first_matching_observation_tick":min((o["tick"] for o in consistent),default=None),
            "witnessed_expected_state":bool(consistent),
            "unselected_outcomes_inferred":False
        })
    count=sum(x["witnessed_expected_state"] for x in results)
    output={
        "schema":SCHEMA,
        "origin":"REAL_FORGE_RCON_AND_FINALIZED_JOURNAL",
        "run_id":finalized["run_id"],
        "configured_world_seed":schedule["configured_world_seed"],
        "schedule_sha256":validated["schedule_sha256"],
        "journal_sha256":finalized["journal_sha256"],
        "interventions_verified":validated["verified_interventions"],
        "interventions_with_matching_direct_observation":count,
        "interventions_without_matching_direct_observation":len(results)-count,
        "observational_coverage_rate":round(count/len(results),6),
        "timing_boundary":"STRICTLY_AFTER_RECORDED_MUTATION_TICK_BEFORE_NEXT_SAME_SOURCE_MUTATION",
        "observed_matching_value_is_not_causal_proof":True,
        "counterfactual_outcomes_inferred":False,
        "learning_or_policy_superiority_claimed":False,
        "minecraft_actions_authorized":False,
        "interventions":results
    }
    unsigned=json.dumps(output,sort_keys=True,separators=(",",":"),allow_nan=False)
    output["sha256"]=hashlib.sha256(unsigned.encode()).hexdigest()
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("schedule",type=Path)
    parser.add_argument("journal",type=Path)
    parser.add_argument("manifest",type=Path)
    parser.add_argument("--world-provenance",type=Path)
    parser.add_argument("--output",type=Path,default=Path("verified-intervention-observation-coverage.json"))
    args=parser.parse_args()
    world=json.loads(args.world_provenance.read_text()) if args.world_provenance else None
    result=audit(json.loads(args.schedule.read_text()),args.journal,args.manifest,world)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("FORGE_INTERVENTION_COVERAGE",result["interventions_with_matching_direct_observation"],
          "of",result["interventions_verified"],"interventions",
          "unseen_not_inferred=true learning_claimed=false")

if __name__=="__main__":
    main()
