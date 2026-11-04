#!/usr/bin/env python3
"""Compare actual scripted and neural Forge attention under matched interventions.

Observation-coverage deltas are descriptive in two different live server runs;
not a randomized treatment estimate or proof of learned generalization.
"""
import argparse
import hashlib
import json
from pathlib import Path

def compare(scripted,neural,verified):
    expected="hearthbound.forge-intervention-observation-coverage.v1"
    for item in (scripted,neural):
        if (item.get("schema")!=expected
            or item.get("origin")!="REAL_FORGE_RCON_AND_FINALIZED_JOURNAL"
            or item.get("interventions_verified")!=6
            or item.get("counterfactual_outcomes_inferred") is not False
            or item.get("minecraft_actions_authorized") is not False
            or item.get("explicit_measurement_window") is not True):
            raise ValueError("invalid verified resource observation coverage")
        digest=item.get("sha256")
        body={k:v for k,v in item.items() if k!="sha256"}
        if hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()!=digest:
            raise ValueError("unverified coverage digest")
    if (verified.get("schema")!="hearthbound.verified-live-neural-intervention.v1"
        or verified.get("origin")!="FINALIZED_REAL_FORGE_ATTENTION"
        or verified.get("scripted_selections_inside_window")!=0
        or verified.get("counterfactual_rewards_inferred") is not False
        or verified.get("neural_policy_outperformed_scripted") is not None
        or not isinstance(verified.get("neural_selected_inspections"),int)
        or verified["neural_selected_inspections"]<1):
        raise ValueError("no verified real neural attention during interventions")
    if (scripted["run_id"]==neural["run_id"]
        or neural["run_id"]!=verified["run_id"]
        or scripted["configured_world_seed"]!=neural["configured_world_seed"]
        or scripted["schedule_sha256"]!=neural["schedule_sha256"]
        or verified["schedule_sha256"]!=neural["schedule_sha256"]
        or verified["configured_world_seed"]!=neural["configured_world_seed"]):
        raise ValueError("attention arms do not share experimental schedule")
    result={
        "schema":"hearthbound.matched-live-forge-attention.v1",
        "origin":"ACTUAL_FINALIZED_FORGE_EXPERIMENT",
        "configured_world_seed":neural["configured_world_seed"],
        "schedule_sha256":neural["schedule_sha256"],
        "scripted_run_id":scripted["run_id"],
        "neural_run_id":neural["run_id"],
        "scripted_witnessed_interventions":scripted["interventions_with_matching_direct_observation"],
        "neural_witnessed_interventions":neural["interventions_with_matching_direct_observation"],
        "scripted_coverage_rate":scripted["observational_coverage_rate"],
        "neural_coverage_rate":neural["observational_coverage_rate"],
        "descriptive_coverage_difference":round(neural["observational_coverage_rate"]-scripted["observational_coverage_rate"],6),
        "verified_neural_selected_inspections":verified["neural_selected_inspections"],
        "same_seed_matched_fixture":True,
        "independent_world_sample":False,
        "randomized_treatment_effect_claimed":False,
        "counterfactual_rewards_inferred":False,
        "learning_generalization_claimed":False
    }
    result["sha256"]=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("scripted_coverage",type=Path)
    p.add_argument("neural_coverage",type=Path)
    p.add_argument("neural_decisions",type=Path)
    p.add_argument("--output",type=Path,default=Path("matched-live-attention-comparison.json"))
    a=p.parse_args()
    result=compare(*(json.loads(path.read_text()) for path in
                     (a.scripted_coverage,a.neural_coverage,a.neural_decisions)))
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("MATCHED_LIVE_FORGE_ATTENTION_COMPARE scripted="+str(result["scripted_witnessed_interventions"])+
          " neural="+str(result["neural_witnessed_interventions"])+
          " causal_superiority_unverified=true")

if __name__=="__main__":
    main()
