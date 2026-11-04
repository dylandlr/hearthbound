#!/usr/bin/env python3
"""Prove real neural-selected inspections happened during seeded interventions.

Counts only recorded selected-source outcomes from a finalized Forge journal.
The comparison is descriptive; no off-policy reward/counterfactual claims.
"""
import argparse
import hashlib
import json
from pathlib import Path
from real_forge_resource_schedule import validate_log

SCHEMA="hearthbound.verified-live-neural-intervention.v1"
NEURAL="NEURAL_CAUSAL_MLP_OPT_IN"
BASELINE="LEAST_RECENTLY_SAMPLED"

def validate(experience,schedule):
    valid=validate_log(schedule)
    if (experience.get("schema")!="hearthbound.verified-citizen-experience.v1"
        or experience.get("origin")!="VERIFIED_REAL_FORGE_ATTENTION_JOURNAL"
        or experience.get("source_finalized") is not True
        or experience.get("learning_performed") is not False
        or experience.get("training_labels_inferred") is not False
        or experience.get("minecraft_actions_authorized") is not False):
        raise ValueError("not a real finalized Forge citizen experience")
    rows=experience.get("transitions")
    if not isinstance(rows,list) or experience.get("records")!=len(rows):
        raise ValueError("inconsistent real citizen decisions")
    first=schedule["executions"][0]["tick_before"]
    end=valid["measurement_stop_tick"]
    if end is None:
        raise ValueError("missing actual experimental cutoff")
    within=[r for r in rows if (type(r.get("decision_tick"))==int
                             and first<r["decision_tick"]<end)]
    neural=[r for r in within if r.get("policy")==NEURAL]
    if not neural:
        raise ValueError("zero neural-controlled inspections during resource experiment")
    if any(r.get("policy")!=NEURAL for r in within):
        raise ValueError("scripted selections occurred during neural intervention window")
    if any(r.get("run_id")!=experience["run_id"] for r in rows):
        raise ValueError("cross-run observations")
    if any(r.get("policy") not in (NEURAL,BASELINE) for r in rows):
        raise ValueError("unrecognized source policy")
    for r in neural:
        if (r.get("selected") not in [x["source"] for x in r["candidate_history_before_choice"]]
            or r.get("unselected_outcomes")!="UNKNOWN"
            or r.get("counterfactual_reward") is not None
            or r.get("optimal_action_label") is not None
            or r.get("new_action_authority") is not False
            or r.get("selected_outcome",{}).get("status") not in ("OBSERVED","UNOBSERVED")):
            raise ValueError("unsafe neural inspection record")
    counts={"OBSERVED":sum(r["selected_outcome"]["status"]=="OBSERVED" for r in neural),
            "UNOBSERVED":sum(r["selected_outcome"]["status"]=="UNOBSERVED" for r in neural)}
    result={"schema":SCHEMA,"origin":"FINALIZED_REAL_FORGE_ATTENTION",
            "run_id":experience["run_id"],
            "configured_world_seed":schedule["configured_world_seed"],
            "schedule_sha256":valid["schedule_sha256"],
            "experiment_start_tick_exclusive":first,
            "experiment_stop_tick_exclusive":end,
            "neural_selected_inspections":len(neural),
            "selected_outcome_counts":counts,
            "scripted_selections_inside_window":0,
            "source_inspection_budget_per_5_ticks":1,
            "model_training_origin":"SIMULATED_CAUSAL_HISTORY_ONLY",
            "neural_policy_outperformed_scripted":None,
            "counterfactual_rewards_inferred":False,
            "task_actions_authorized":False}
    result["sha256"]=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("experience",type=Path)
    parser.add_argument("schedule",type=Path)
    parser.add_argument("--output",type=Path,default=Path("verified-live-neural-intervention.json"))
    args=parser.parse_args()
    report=validate(json.loads(args.experience.read_text()),json.loads(args.schedule.read_text()))
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("LIVE_FORGE_NEURAL_INTERVENTION_PASS selections="+str(report["neural_selected_inspections"])+
          " real_forge=true reward_advantage=UNKNOWN")

if __name__=="__main__":
    main()
