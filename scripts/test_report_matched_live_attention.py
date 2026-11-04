#!/usr/bin/env python3
"""Reject counterfeit or mismatched real Forge attention comparisons."""
import hashlib
import json
from report_matched_live_attention import compare

def coverage(run,seed="probe-A",schedule="a"*64,count=5):
    d={
        "schema":"hearthbound.forge-intervention-observation-coverage.v1",
        "origin":"REAL_FORGE_RCON_AND_FINALIZED_JOURNAL",
        "run_id":run,"configured_world_seed":seed,
        "schedule_sha256":schedule,"interventions_verified":6,
        "explicit_measurement_window":True,
        "interventions_with_matching_direct_observation":count,
        "observational_coverage_rate":round(count/6,6),
        "counterfactual_outcomes_inferred":False,
        "minecraft_actions_authorized":False
    }
    d["sha256"]=hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return d

def denied(a,b,n):
    try:compare(a,b,n)
    except ValueError:return
    raise AssertionError("invalid comparison was accepted")

def main():
    a=coverage("scripted")
    b=coverage("neural",count=6)
    n={"schema":"hearthbound.verified-live-neural-intervention.v1",
       "origin":"FINALIZED_REAL_FORGE_ATTENTION",
       "run_id":"neural","configured_world_seed":"probe-A",
       "schedule_sha256":"a"*64,
       "scripted_selections_inside_window":0,
       "neural_selected_inspections":4,
       "counterfactual_rewards_inferred":False,
       "neural_policy_outperformed_scripted":None}
    result=compare(a,b,n)
    assert result["verified_neural_selected_inspections"]==4
    assert result["descriptive_coverage_difference"]==round(1.-round(5/6,6),6)
    assert result["randomized_treatment_effect_claimed"] is False
    assert result["counterfactual_rewards_inferred"] is False
    denied(a,a,n)
    denied(a,coverage("neural",seed="other"),n)
    denied(a,coverage("neural",schedule="b"*64),n)
    changed=json.loads(json.dumps(b))
    changed["interventions_with_matching_direct_observation"]=3
    denied(a,changed,n)
    broken=json.loads(json.dumps(n))
    broken["scripted_selections_inside_window"]=1
    denied(a,b,broken)
    broken=json.loads(json.dumps(n))
    broken["neural_selected_inspections"]=0
    denied(a,b,broken)
    print("MATCHED_LIVE_ATTENTION_COMPARISON_TESTS_PASS")

if __name__=="__main__":
    main()
