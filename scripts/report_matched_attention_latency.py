#!/usr/bin/env python3
"""Compare real Forge attention latency per intervention and configured seed.

Only actual sealed-journal selected-source receipts are used. Mutations happen
at different server ticks in separately executed arms, so these are descriptive
timing differences, NOT paired identical-tick causal treatment outcomes.
"""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

SCHEMA="hearthbound.forge-attention-latency-pair.v1"
SOURCE_SCHEMA="hearthbound.forge-intervention-observation-coverage.v1"

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)

def verified_report(r):
    if (not isinstance(r,dict) or r.get("schema")!=SOURCE_SCHEMA
        or r.get("origin")!="REAL_FORGE_RCON_AND_FINALIZED_JOURNAL"
        or r.get("explicit_measurement_window") is not True
        or r.get("counterfactual_outcomes_inferred") is not False
        or r.get("minecraft_actions_authorized") is not False
        or r.get("learning_or_policy_superiority_claimed") is not False
        or r.get("observed_matching_value_is_not_causal_proof") is not True):
        raise ValueError("invalid observational Forge coverage evidence")
    digest=r.get("sha256")
    body={k:v for k,v in r.items() if k!="sha256"}
    if not isinstance(digest,str) or hashlib.sha256(canonical(body).encode()).hexdigest()!=digest:
        raise ValueError("invalid Forge coverage digest")
    events=r.get("interventions")
    if (r.get("interventions_verified")!=6 or not isinstance(events,list)
        or len(events)!=6 or type(r.get("measurement_stop_tick"))!=int):
        raise ValueError("invalid intervention count or stop tick")
    seen=0
    previous=-1
    measurements=[]
    for i,e in enumerate(events,1):
        if not isinstance(e,dict) or set(e)!={
            "intervention_index","source","wheat_after_operator_mutation",
            "mutation_tick_after","window_end_exclusive",
            "direct_selected_observations_in_window",
            "observations_matching_expected_wheat",
            "observations_not_matching_expected_wheat",
            "first_matching_observation_tick","witnessed_expected_state",
            "unselected_outcomes_inferred"}:
            raise ValueError("invalid real intervention fields")
        start=e["mutation_tick_after"]
        stop=e["window_end_exclusive"]
        count=e["direct_selected_observations_in_window"]
        matches=e["observations_matching_expected_wheat"]
        misses=e["observations_not_matching_expected_wheat"]
        tick=e["first_matching_observation_tick"]
        if (type(e["intervention_index"])!=int or e["intervention_index"]!=i
            or not isinstance(e["source"],str) or not e["source"]
            or type(e["wheat_after_operator_mutation"])!=int
            or type(start)!=int or type(stop)!=int
            or start<previous or stop<=start or stop>r["measurement_stop_tick"]
            or any(type(x)!=int or x<0 for x in (count,matches,misses))
            or matches+misses!=count
            or e["unselected_outcomes_inferred"] is not False
            or type(e["witnessed_expected_state"])!=bool
            or e["witnessed_expected_state"]!=(matches>0)
            or ((tick is None)!=(matches==0))
            or (tick is not None and (type(tick)!=int or not start<tick<stop))):
            raise ValueError("inconsistent witness event or tick ordering")
        previous=start
        seen+=int(tick is not None)
        measurements.append({
            "index":i,"source":e["source"],
            "wheat":e["wheat_after_operator_mutation"],
            "observed":tick is not None,
            "latency_ticks":None if tick is None else tick-start,
            "censor_window_ticks":stop-start,
            "selected_source_inspections":count,
            "contradictory_observations":misses})
    if (seen!=r["interventions_with_matching_direct_observation"]
        or len(measurements)-seen!=r["interventions_without_matching_direct_observation"]
        or r["observational_coverage_rate"]!=round(seen/6,6)):
        raise ValueError("inconsistent overall intervention count")
    return measurements

def pair(scripted,neural):
    a=verified_report(scripted)
    b=verified_report(neural)
    if (scripted.get("run_id")==neural.get("run_id")
        or scripted.get("configured_world_seed")!=neural.get("configured_world_seed")
        or scripted.get("schedule_sha256")!=neural.get("schedule_sha256")):
        raise ValueError("different source schedules or duplicate real run")
    for x,y in zip(a,b):
        if (x["index"],x["source"],x["wheat"])!=(y["index"],y["source"],y["wheat"]):
            raise ValueError("scheduled resource intervention mismatch")
    def summarize(events):
        observed=[e["latency_ticks"] for e in events if e["observed"]]
        return {
            "witnessed_events":len(observed),
            "unwitnessed_events":len(events)-len(observed),
            "mean_observed_first_witness_latency_ticks":
                round(statistics.mean(observed),4) if observed else None,
            "median_observed_first_witness_latency_ticks":
                round(statistics.median(observed),4) if observed else None,
            "direct_selected_inspections_during_windows":
                sum(e["selected_source_inspections"] for e in events),
            "contradictory_selected_observations":
                sum(e["contradictory_observations"] for e in events),
        }
    entries=[{"index":x["index"],"source":x["source"],"wheat":x["wheat"],
              "scripted_first_witness_ticks":x["latency_ticks"],
              "neural_first_witness_ticks":y["latency_ticks"],
              "both_witnessed":x["observed"] and y["observed"],
              "descriptive_neural_minus_scripted_ticks":
                  y["latency_ticks"]-x["latency_ticks"]
                  if x["observed"] and y["observed"] else None,
              "server_tick_trajectories_identical":False}
             for x,y in zip(a,b)]
    comparable=[v["descriptive_neural_minus_scripted_ticks"] for v in entries
                if v["both_witnessed"]]
    out={
        "schema":SCHEMA,
        "origin":"REAL_FORGE_VERIFIED_SELECTED_SOURCE_OBSERVATIONS",
        "configured_world_seed":scripted["configured_world_seed"],
        "schedule_sha256":scripted["schedule_sha256"],
        "scripted_run_id":scripted["run_id"],
        "neural_run_id":neural["run_id"],
        "scripted":summarize(a),
        "neural":summarize(b),
        "both_witnessed_events":len(comparable),
        "mean_descriptive_neural_minus_scripted_latency_ticks":
            round(statistics.mean(comparable),4) if comparable else None,
        "per_intervention":entries,
        "identical_stimulus_timing_verified":False,
        "independent_world_conditions_verified":False,
        "causal_latency_advantage_claimed":False,
        "unselected_counterfactual_outcomes_inferred":False,
    }
    out["sha256"]=hashlib.sha256(canonical(out).encode()).hexdigest()
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("scripted",type=Path)
    parser.add_argument("neural",type=Path)
    parser.add_argument("--output",type=Path,default=Path("forge-attention-latency-pair.json"))
    a=parser.parse_args()
    report=pair(json.loads(a.scripted.read_text()),json.loads(a.neural.read_text()))
    a.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("REAL_FORGE_ATTENTION_LATENCY verified_events="+str(report["both_witnessed_events"])
          +" descriptive_delay="+str(report["mean_descriptive_neural_minus_scripted_latency_ticks"])
          +" causal_advantage_unverified=true")

if __name__=="__main__":
    main()
