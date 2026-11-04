#!/usr/bin/env python3
"""Deterministic contracts for real Forge attention latency attribution."""
import hashlib
import json
from report_matched_attention_latency import pair,canonical

def report(run_id,seed="probe-A",schedule="a"*64,latencies=(1,2,3,4,5,6)):
    events=[]
    for i,latency in enumerate(latencies):
        tick=100+i*40
        seen=latency is not None
        events.append({
            "intervention_index":i+1,
            "source":"9 100 2" if i%2==0 else "10 100 2",
            "wheat_after_operator_mutation":(i%4)+1,
            "mutation_tick_after":tick,
            "window_end_exclusive":tick+30,
            "direct_selected_observations_in_window":1 if seen else 0,
            "observations_matching_expected_wheat":1 if seen else 0,
            "observations_not_matching_expected_wheat":0,
            "first_matching_observation_tick":tick+latency if seen else None,
            "witnessed_expected_state":seen,
            "unselected_outcomes_inferred":False
        })
    n=sum(x["witnessed_expected_state"] for x in events)
    data={
        "schema":"hearthbound.forge-intervention-observation-coverage.v1",
        "origin":"REAL_FORGE_RCON_AND_FINALIZED_JOURNAL",
        "explicit_measurement_window":True,
        "counterfactual_outcomes_inferred":False,
        "minecraft_actions_authorized":False,
        "learning_or_policy_superiority_claimed":False,
        "observed_matching_value_is_not_causal_proof":True,
        "run_id":run_id,"configured_world_seed":seed,
        "schedule_sha256":schedule,
        "interventions_verified":6,
        "measurement_stop_tick":400,
        "interventions":events,
        "interventions_with_matching_direct_observation":n,
        "interventions_without_matching_direct_observation":6-n,
        "observational_coverage_rate":round(n/6,6)
    }
    data["sha256"]=hashlib.sha256(canonical(data).encode()).hexdigest()
    return data

def invalid(a,b):
    try:pair(a,b)
    except ValueError:return
    raise AssertionError("Invalid timing report accepted")

def resign(x):
    x.pop("sha256")
    x["sha256"]=hashlib.sha256(canonical(x).encode()).hexdigest()
    return x

def main():
    scripted=report("scripted")
    neural=report("neural",latencies=(6,5,4,3,2,1))
    result=pair(scripted,neural)
    assert result["both_witnessed_events"]==6
    assert result["scripted"]["mean_observed_first_witness_latency_ticks"]==3.5
    assert result["neural"]["mean_observed_first_witness_latency_ticks"]==3.5
    assert result["mean_descriptive_neural_minus_scripted_latency_ticks"]==0.
    assert result["causal_latency_advantage_claimed"] is False
    assert result==pair(scripted,neural)
    invalid(scripted,scripted)
    invalid(scripted,report("neural",seed="probe-B"))
    invalid(scripted,report("neural",schedule="b"*64))
    broken=json.loads(json.dumps(neural))
    broken["interventions"][0]["first_matching_observation_tick"]=100
    invalid(scripted,resign(broken))
    broken=json.loads(json.dumps(neural))
    broken["interventions"][0]["source"]="11 100 2"
    invalid(scripted,resign(broken))
    broken=json.loads(json.dumps(neural))
    broken["interventions"][0]["observations_not_matching_expected_wheat"]=1
    invalid(scripted,resign(broken))
    broken=json.loads(json.dumps(neural))
    broken["interventions_with_matching_direct_observation"]=5
    invalid(scripted,resign(broken))
    broken=json.loads(json.dumps(neural))
    broken["interventions"][0]["first_matching_observation_tick"]=None
    invalid(scripted,resign(broken))
    partial=pair(report("scripted",latencies=(1,None,3,4,5,6)),
                 report("neural",latencies=(2,2,4,None,6,5)))
    assert partial["both_witnessed_events"]==4
    assert partial["scripted"]["unwitnessed_events"]==1
    assert partial["neural"]["unwitnessed_events"]==1
    print("REAL_FORGE_ATTENTION_LATENCY_CONTRACT_PASS")

if __name__=="__main__":
    main()
