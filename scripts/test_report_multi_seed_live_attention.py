#!/usr/bin/env python3
"""Regression checks for run-level seeded-attention comparisons."""
import hashlib
import json
from report_multi_seed_live_attention import aggregate,canonical

def report(index,scripted=6,neural=6):
    seed="hearthbound-resource-probe-"+chr(65+index)
    x={"schema":"hearthbound.matched-live-forge-attention.v1",
       "origin":"ACTUAL_FINALIZED_FORGE_EXPERIMENT",
       "configured_world_seed":seed,
       "schedule_sha256":hashlib.sha256(seed.encode()).hexdigest(),
       "scripted_run_id":"scripted-"+str(index),
       "neural_run_id":"neural-"+str(index),
       "scripted_witnessed_interventions":scripted,
       "neural_witnessed_interventions":neural,
       "scripted_coverage_rate":round(scripted/6,6),
       "neural_coverage_rate":round(neural/6,6),
       "descriptive_coverage_difference":round(round(neural/6,6)-round(scripted/6,6),6),
       "verified_neural_selected_inspections":13,
       "same_seed_matched_fixture":True,
       "independent_world_sample":False,
       "randomized_treatment_effect_claimed":False,
       "counterfactual_rewards_inferred":False,
       "learning_generalization_claimed":False}
    x["sha256"]=hashlib.sha256(canonical(x).encode()).hexdigest()
    return x

def rejected(reports):
    try:aggregate(reports)
    except ValueError:return
    raise AssertionError("Invalid multiseed evidence was accepted")

def main():
    values=[report(0),report(1,5,4),report(2,4,5)]
    x=aggregate(values)
    assert x==aggregate(list(reversed(values))),"Order changes report"
    assert x["configured_seed_pairs"]==3
    assert x["total_real_server_runs"]==6
    assert not x["all_arms_at_ceiling"]
    assert x["statistical_significance_claimed"] is False
    assert x["generalization_claim_allowed"] is False
    assert x["world_diversity_independently_validated"] is False
    assert x["unweighted_mean_paired_difference"]==0.
    rejected(values[:2])
    rejected([values[0],values[0],values[2]])
    corrupted=json.loads(json.dumps(values))
    corrupted[1]["neural_coverage_rate"]=0.
    rejected(corrupted)
    corrupted=json.loads(json.dumps(values))
    corrupted[1]["independent_world_sample"]=True
    corrupted[1].pop("sha256")
    corrupted[1]["sha256"]=hashlib.sha256(canonical(corrupted[1]).encode()).hexdigest()
    rejected(corrupted)
    corrupted=json.loads(json.dumps(values))
    corrupted[1]["neural_run_id"]=corrupted[0]["neural_run_id"]
    corrupted[1].pop("sha256")
    corrupted[1]["sha256"]=hashlib.sha256(canonical(corrupted[1]).encode()).hexdigest()
    rejected(corrupted)
    at_ceiling=aggregate([report(i) for i in range(3)])
    assert at_ceiling["all_arms_at_ceiling"] and at_ceiling["unweighted_mean_paired_difference"]==0
    print("MULTISEED_REAL_FORGE_ATTENTION_CONTRACT_PASS")

if __name__=="__main__":
    main()
