#!/usr/bin/env python3
"""Fail-closed event-delay audit. Not an authorization for Forge deployment."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

ARMS=("scripted","greedy_forecast","age_blend","coverage_guard")
SCHEDULES=("permanent_depletion","bursty_mutations","long_observation_gaps")
SCHEMA="hearthbound.attention-event-latency-admission.v1"

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)

def audit(report):
    unsigned={k:v for k,v in report.items() if k!="sha256"}
    if (report.get("schema")!="hearthbound.attention-event-latency.v1"
        or report.get("sha256")!=hashlib.sha256(canonical(unsigned).encode()).hexdigest()
        or report.get("origin")!="SIMULATOR_ONLY_EVENT_JOURNAL_AUDIT"
        or report.get("missed_event_censoring")!="REMAINING_HORIZON_STEPS_FROM_TRANSITION"
        or report.get("agent_can_read_hidden_transition_log") is not False
        or report.get("event_outcomes_used_for_training") is not False
        or report.get("model_promotion_authorized") is not False):
        raise ValueError("invalid signed event evidence")
    seeds=report.get("train_seeds")
    cells=report.get("cells")
    if (not isinstance(seeds,list) or len(seeds)<3 or len(set(seeds))!=len(seeds)
        or not isinstance(cells,list) or len(cells)!=len(seeds)*3):
        raise ValueError("missing independent seed/schedule cells")
    seen=set()
    rows={arm:{schedule:[] for schedule in SCHEDULES} for arm in ARMS}
    by_seed={arm:{seed:[] for seed in seeds} for arm in ARMS}
    for cell in cells:
        seed=cell.get("training_seed")
        schedule=cell.get("schedule")
        key=(seed,schedule)
        if (seed not in seeds or schedule not in SCHEDULES or key in seen
            or cell.get("heldout_episodes")!=report.get("heldout_episodes_per_schedule")
            or cell.get("frozen_model_sha256")!=report.get("model_hashes",{}).get(str(seed))):
            raise ValueError("duplicate or inconsistent event trial")
        seen.add(key)
        metrics=cell.get("mean_by_arm")
        pairs=cell.get("paired_against_scripted")
        if (not isinstance(metrics,dict) or set(metrics)!=set(ARMS)
            or not isinstance(pairs,dict) or set(pairs)!=set(ARMS[1:])):
            raise ValueError("missing paired evidence")
        for arm in ARMS:
            m=metrics[arm]
            if (m["mean_latent_transition_count"]<m["mean_witnessed_latent_events"]
                or m["mean_total_censored_event_delay"]<m["mean_total_detection_delay"]
                or m["mean_unproductive_reinspections"]<0):
                raise ValueError("invalid event accounting")
            rows[arm][schedule].append(m)
            by_seed[arm][seed].append(m)
        for arm in ARMS[1:]:
            d=pairs[arm]
            for keyname,mname in (
                ("witnessed_event_differences","mean_witnessed_latent_events"),
                ("censored_event_delay_differences","mean_total_censored_event_delay"),
                ("direct_reinspection_difference","mean_direct_reinspection_disagreements")):
                values=d.get(keyname)
                if (not isinstance(values,list) or len(values)!=cell["heldout_episodes"]
                    or any(type(v) not in (float,int) for v in values)
                    or abs(statistics.mean(values)-
                        (metrics[arm][mname]-metrics["scripted"][mname]))>0.000002):
                    raise ValueError("paired differences do not match direct journals")
    summary={}
    for arm in ARMS:
        summary[arm]={}
        for schedule in SCHEDULES:
            samples=rows[arm][schedule]
            summary[arm][schedule]={
                "witnessed_events":round(statistics.mean(
                    x["mean_witnessed_latent_events"] for x in samples),6),
                "censored_delay":round(statistics.mean(
                    x["mean_total_censored_event_delay"] for x in samples),6),
                "unproductive_reinspections":round(statistics.mean(
                    x["mean_unproductive_reinspections"] for x in samples),6)}
    # A rejection-only requirement: can't win by detecting fewer events.
    age_noninferior=all(
        summary["age_blend"][sc]["witnessed_events"]>=
        summary["scripted"][sc]["witnessed_events"]-0.000002 and
        summary["age_blend"][sc]["censored_delay"]<=
        summary["scripted"][sc]["censored_delay"]+0.000002
        for sc in SCHEDULES)
    output={
        "schema":SCHEMA,"origin":"VERIFIED_SYNTHETIC_EVENT_AUDIT",
        "seed_count":len(seeds),"paired_schedule_cells":len(cells),
        "schedule_summary":summary,
        "age_blend_coverage_and_censored_latency_noninferior":age_noninferior,
        "age_blend_accepted_for_minecraft":False,
        "real_forge_generalization_established":False,
        "model_promotion_authorized":False}
    output["sha256"]=hashlib.sha256(canonical(output).encode()).hexdigest()
    return output

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input",type=Path)
    ap.add_argument("--output",type=Path,default=Path("attention-event-admission.json"))
    args=ap.parse_args()
    result=audit(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("EVENT_COVERAGE_CENSORED_LATENCY_NONINFERIOR="+
          str(result["age_blend_coverage_and_censored_latency_noninferior"]).lower()+
          " minecraft_promotion=false")
if __name__=="__main__":
    main()
