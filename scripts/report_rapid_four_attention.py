#!/usr/bin/env python3
"""Descriptive real Forge 4-source contention comparison, not causal inference."""
import argparse
import hashlib
import json
from pathlib import Path

INPUT="hearthbound.rapid-four-attention-coverage.v1"
SCHEMA="hearthbound.rapid-four-matched-attention.v1"

def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def compare(scripted,neural):
    names=("LEAST_RECENTLY_SAMPLED","NEURAL_CAUSAL_MLP_OPT_IN")
    for report,name in ((scripted,names[0]),(neural,names[1])):
        unsigned={k:v for k,v in report.items() if k!="sha256"}
        if (report.get("schema")!=INPUT
            or report.get("origin")!="REAL_FORGE_RCON_AND_FINALIZED_CITIZEN_JOURNAL"
            or report.get("policy")!=name
            or report.get("sha256")!=digest(unsigned)
            or report.get("total_registered_sources")!=4
            or report.get("verified_mutations")!=16
            or report.get("counterfactual_outcomes_inferred") is not False
            or report.get("claim_of_neural_superiority") is not False
            or type(report.get("witnessed_interventions"))!=int
            or type(report.get("unwitnessed_interventions"))!=int
            or report["witnessed_interventions"]<0
            or report["unwitnessed_interventions"]<0
            or report["witnessed_interventions"]+report["unwitnessed_interventions"]!=16
            or report.get("witness_rate")!=round(report["witnessed_interventions"]/16,6)
            or type(report.get("verified_selected_inspections"))!=int
            or report["verified_selected_inspections"]<1):
            raise ValueError("invalid real challenge coverage report")
    if (scripted.get("run_id")==neural.get("run_id")
        or scripted.get("configured_world_seed")!=neural.get("configured_world_seed")
        or scripted.get("plan_sha256")!=neural.get("plan_sha256")):
        raise ValueError("mismatched real Forge challenge arms")
    a=scripted.get("interventions")
    b=neural.get("interventions")
    if not isinstance(a,list) or not isinstance(b,list) or len(a)!=16 or len(b)!=16:
        raise ValueError("missing source intervention receipts")
    for index,(x,y) in enumerate(zip(a,b),1):
        for event in (x,y):
            if (event.get("intervention_index")!=index
                or type(event.get("matching_state_witnessed"))!=bool
                or type(event.get("direct_selected_observations"))!=int
                or event["direct_selected_observations"]<0
                or type(event.get("mutation_tick_after"))!=int
                or type(event.get("window_end_exclusive"))!=int
                or event["window_end_exclusive"]<event["mutation_tick_after"]
                or (event.get("first_witness_latency_ticks") is None)!=(
                    not event["matching_state_witnessed"])):
                raise ValueError("invalid source witness event")
            if event["matching_state_witnessed"]:
                if (type(event["first_witness_latency_ticks"])!=int
                    or not 0<event["first_witness_latency_ticks"]<
                    event["window_end_exclusive"]-event["mutation_tick_after"]):
                    raise ValueError("invalid first witness tick")
        if (x["source"],x["wheat"])!=(y["source"],y["wheat"]):
            raise ValueError("different commanded resource sequences")
    if (sum(x["matching_state_witnessed"] for x in a)!=scripted["witnessed_interventions"]
        or sum(x["matching_state_witnessed"] for x in b)!=neural["witnessed_interventions"]):
        raise ValueError("witness count does not match finalized events")
    result={
        "schema":SCHEMA,
        "origin":"MATCHED_REAL_FORGE_FOUR_SOURCE_FIXTURE",
        "configured_world_seed":scripted["configured_world_seed"],
        "plan_sha256":scripted["plan_sha256"],
        "scripted_run_id":scripted["run_id"],
        "neural_run_id":neural["run_id"],
        "scripted_witnessed_of_16":scripted["witnessed_interventions"],
        "neural_witnessed_of_16":neural["witnessed_interventions"],
        "scripted_selected_inspections":scripted["verified_selected_inspections"],
        "neural_selected_inspections":neural["verified_selected_inspections"],
        "descriptive_neural_minus_scripted_witness_count":
            neural["witnessed_interventions"]-scripted["witnessed_interventions"],
        "four_sources_competing":True,
        "one_inspection_per_five_ticks":True,
        "identical_tick_aligned_stimuli_verified":False,
        "independent_environment_generalization_claimed":False,
        "statistical_significance_claimed":False,
        "causal_neural_superiority_claimed":False,
        "counterfactual_outcomes_inferred":False
    }
    result["sha256"]=digest(result)
    return result

def main():
    c=argparse.ArgumentParser()
    c.add_argument("scripted",type=Path)
    c.add_argument("neural",type=Path)
    c.add_argument("--output",type=Path,default=Path("rapid-four-matched-comparison.json"))
    opts=c.parse_args()
    output=compare(json.loads(opts.scripted.read_text()),json.loads(opts.neural.read_text()))
    opts.output.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print("REAL_FORGE_FOUR_SOURCE_COMPARE scripted="+str(output["scripted_witnessed_of_16"])+
          " neural="+str(output["neural_witnessed_of_16"])+
          " evidence=REAL_FORGE generalized=false")

if __name__=="__main__":
    main()
