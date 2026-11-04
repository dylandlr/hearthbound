#!/usr/bin/env python3
"""Reject forged and mismatched four-source Forge attention reports."""
import json
from report_rapid_four_attention import compare,digest
from rapid_four_source_schedule import plan

def fixture(policy,run,witnesses=7):
    schedule=plan("hearthbound-rapid-four-D")
    events=[]
    for i,step in enumerate(schedule["steps"]):
        tick=100+i*10
        seen=i<witnesses
        events.append({
            "intervention_index":step["index"],
            "source":step["source"],"wheat":step["wheat"],
            "mutation_tick_after":tick,"window_end_exclusive":tick+8,
            "direct_selected_observations":1 if seen else 0,
            "matching_state_witnessed":seen,
            "first_witness_latency_ticks":2 if seen else None})
    item={
        "schema":"hearthbound.rapid-four-attention-coverage.v1",
        "origin":"REAL_FORGE_RCON_AND_FINALIZED_CITIZEN_JOURNAL",
        "run_id":run,
        "configured_world_seed":"hearthbound-rapid-four-D",
        "plan_sha256":schedule["sha256"],"policy":policy,
        "total_registered_sources":4,
        "verified_mutations":16,
        "verified_selected_inspections":9,
        "witnessed_interventions":witnesses,
        "unwitnessed_interventions":16-witnesses,
        "witness_rate":round(witnesses/16,6),
        "counterfactual_outcomes_inferred":False,
        "claim_of_neural_superiority":False,
        "interventions":events}
    item["sha256"]=digest(item)
    return item

def reject(a,b):
    try:compare(a,b)
    except ValueError:return
    raise AssertionError("invalid four-source real comparison accepted")

def resign(x):
    x.pop("sha256")
    x["sha256"]=digest(x)
    return x

def main():
    a=fixture("LEAST_RECENTLY_SAMPLED","scripted")
    b=fixture("NEURAL_CAUSAL_MLP_OPT_IN","neural",9)
    result=compare(a,b)
    assert result["descriptive_neural_minus_scripted_witness_count"]==2
    assert result["counterfactual_outcomes_inferred"] is False
    assert result["causal_neural_superiority_claimed"] is False
    reject(a,a)
    bad=json.loads(json.dumps(b));bad["configured_world_seed"]="other"
    reject(a,resign(bad))
    bad=json.loads(json.dumps(b));bad["interventions"][1]["source"]="99 100 2"
    reject(a,resign(bad))
    bad=json.loads(json.dumps(b));bad["interventions"][1]["first_witness_latency_ticks"]=0
    reject(a,resign(bad))
    bad=json.loads(json.dumps(b));bad["witnessed_interventions"]=10
    reject(a,resign(bad))
    bad=json.loads(json.dumps(b));bad["policy"]="LEAST_RECENTLY_SAMPLED"
    reject(a,resign(bad))
    print("REAL_FORGE_RAPID_FOUR_COMPARISON_CONTRACT_PASS")

if __name__=="__main__":
    main()
