#!/usr/bin/env python3
"""Audit rapid-four real Forge source-state witnesses within valid tick windows.

Reads finalized citizen attention journal, never current chest inventories.
Unobserved intervening changes remain unknown to the citizen.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from rapid_four_source_schedule import verify,SOURCES
from validate_forge_attention_manifest import verify as verified_manifest
from validate_forge_attention_pair import pair

SCHEMA="hearthbound.rapid-four-attention-coverage.v1"

def audit(execution,journal,manifest):
    confirmed=verify(execution)
    sealed=verified_manifest(Path(journal),Path(manifest),minimum=1)
    records=[json.loads(line) for line in Path(journal).read_text().splitlines()]
    source_events=[]
    observed_policies=set()
    start_tick=execution["executions"][0]["tick_before"]
    stop_tick=execution["measurement_stop_tick"]
    for record in records:
        encoded=record["payload_b64"]
        decoded=base64.urlsafe_b64decode(encoded+"="*((-len(encoded))%4)).decode()
        before,after=decoded.split("\n")
        event=pair(before,after)
        opp=event["opportunity"]
        out=event["outcome"]
        # Startup registration and post-cutoff cleanup are not part of the
        # four-choice contention treatment.
        if not start_tick<opp["tick"]<stop_tick:
            continue
        if len(opp["candidates"])!=4 or set(opp["candidates"])!=set(
            source.replace(" ",",") for source in SOURCES):
            raise ValueError("Challenge did not present exactly four registered sources")
        observed_policies.add(opp["policy"])
        source_events.append({"tick":opp["tick"],
            "source":opp["selected"].replace(","," "),
            "policy":opp["policy"],
            "status":out["status"],"wheat":out["wheat"]})
    expected=execution["policy"]
    if expected not in ("LEAST_RECENTLY_SAMPLED","NEURAL_CAUSAL_MLP_OPT_IN"):
        raise ValueError("unknown actual choice policy")
    if not source_events:
        raise ValueError("No real citizen attention decisions during the rapid experiment")
    if observed_policies!={expected}:
        raise ValueError("real selected-source journal was not exclusively assigned to intended policy")
    previous=-1
    for item in source_events:
        if item["tick"]<previous:raise ValueError("non-chronological real observations")
        previous=item["tick"]
    results=[]
    mutations=execution["executions"]
    for i,m in enumerate(mutations):
        later=[v["tick_before"] for v in mutations[i+1:] if v["source"]==m["source"]]
        stop=min(later) if later else execution["measurement_stop_tick"]
        if stop<m["tick_after"]:raise ValueError("overlapping mutation intervals")
        window=[v for v in source_events if m["tick_after"]<v["tick"]<stop
                and v["source"]==m["source"] and v["status"]=="OBSERVED"]
        consistent=[v for v in window if v["wheat"]==m["wheat"]]
        first=min((v["tick"] for v in consistent),default=None)
        results.append({"intervention_index":m["index"],
                        "source":m["source"],
                        "wheat":m["wheat"],
                        "mutation_tick_after":m["tick_after"],
                        "window_end_exclusive":stop,
                        "direct_selected_observations":len(window),
                        "matching_state_witnessed":first is not None,
                        "first_witness_latency_ticks":None if first is None
                            else first-m["tick_after"]})
    n=sum(x["matching_state_witnessed"] for x in results)
    answer={
        "schema":SCHEMA,
        "origin":"REAL_FORGE_RCON_AND_FINALIZED_CITIZEN_JOURNAL",
        "run_id":sealed["run_id"],
        "journal_sha256":sealed["journal_sha256"],
        "configured_world_seed":execution["configured_world_seed"],
        "plan_sha256":confirmed["plan_sha256"],
        "policy":expected,
        "total_registered_sources":4,
        "verified_mutations":len(mutations),
        "verified_selected_inspections":len(source_events),
        "witnessed_interventions":n,
        "unwitnessed_interventions":len(mutations)-n,
        "witness_rate":round(n/len(mutations),6),
        "counterfactual_outcomes_inferred":False,
        "claim_of_neural_superiority":False,
        "interventions":results}
    canonical=json.dumps(answer,sort_keys=True,separators=(",",":"),allow_nan=False)
    answer["sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    return answer

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("execution",type=Path)
    cli.add_argument("journal",type=Path)
    cli.add_argument("manifest",type=Path)
    cli.add_argument("--output",type=Path,default=Path("rapid-four-observation-coverage.json"))
    args=cli.parse_args()
    report=audit(json.loads(args.execution.read_text()),args.journal,args.manifest)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("RAPID_FOUR_REAL_FORGE_WITNESSED "+str(report["witnessed_interventions"])+
          "/"+str(report["verified_mutations"])+
          " policy="+report["policy"]+" unselected=UNKNOWN")

if __name__=="__main__":
    main()
