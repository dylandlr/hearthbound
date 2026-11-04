#!/usr/bin/env python3
"""Read-only policy agreement on causally exported real Forge decisions.

No alternate-source rewards are inferred. A trained MLP originates solely in
the abstract simulator, never from these held-out Minecraft records.
"""
import argparse
import hashlib
import json
from pathlib import Path

from evaluate_causal_attention_history import train as train_synthetic
from train_simulated_attention_mlp import SOURCES, WIDTH

SCHEMA="hearthbound.real-attention-shadow-comparison.v1"

def model_features(history):
    if len(history)>SOURCES:
        raise ValueError("More candidates than frozen simulator network supports")
    vector=[]
    for candidate in history:
        age=candidate["age_ticks"]
        if age is not None and (type(age)!=int or age<0):
            raise ValueError("Invalid age")
        seen=candidate["status"]=="KNOWN"
        if candidate["status"] not in ("KNOWN","UNKNOWN"):
            raise ValueError("Invalid memory state")
        if not seen and (candidate["last_observed_available"] is not None
                         or candidate["last_observed_wheat"] is not None
                         or age is not None
                         or candidate["direct_observation_count"]!=0
                         or candidate["observed_change_rate"] is not None):
            raise ValueError("Unseen source contains forbidden history")
        if seen and (type(candidate["last_observed_available"])!=bool
                     or type(candidate["direct_observation_count"])!=int
                     or candidate["direct_observation_count"]<1):
            raise ValueError("Invalid witnessed history")
        rate=candidate["observed_change_rate"]
        if rate is not None and (type(rate) not in (int,float) or not 0<=rate<=1):
            raise ValueError("Invalid history estimate")
        # 20 simulator decisions correspond to 100 Minecraft ticks at the
        # configured one-decision-per-five-ticks budget. This is transfer
        # scaling, not a validated calibration.
        vector.extend([float(not seen),
                       float(candidate["last_observed_available"] is True),
                       1.0 if age is None else min(age/100.,1.),
                       .5 if rate is None else float(rate)])
    vector.extend([0.,0.,0.,.5]*(SOURCES-len(history)))
    assert len(vector)==WIDTH
    return vector

def recommend(history,model,policy):
    if not history:raise ValueError("No candidates")
    if policy=="simulator_trained_mlp":
        scores=model.values(model_features(history))[2] if hasattr(model,"values") else model.forward(model_features(history))[2]
        return history[max(range(len(history)),key=lambda i:(scores[i],-i))]["source"]
    if policy=="unknown_first_then_oldest":
        # A stronger observation-only heuristic, *not* the actual attempted-
        # rotation Forge baseline (which tracks attempted inspection recency).
        return max(history,key=lambda x:(
            int(x["status"]=="UNKNOWN"),
            x["age_ticks"] if x["age_ticks"] is not None else 0,
            -history.index(x)))["source"]
    if policy=="first_registered":
        return history[0]["source"]
    raise ValueError("Unknown policy")

def compare(dataset,model):
    if (dataset.get("schema")!="hearthbound.verified-citizen-experience.v1"
        or dataset.get("origin")!="VERIFIED_REAL_FORGE_ATTENTION_JOURNAL"
        or dataset.get("source_finalized") is not True
        or dataset.get("learning_performed") is not False
        or dataset.get("training_labels_inferred") is not False
        or dataset.get("minecraft_actions_authorized") is not False):
        raise ValueError("Dataset lacks finalized Forge provenance")
    rows=dataset.get("transitions")
    if not isinstance(rows,list) or not rows or dataset.get("records")!=len(rows):
        raise ValueError("Invalid citizen experience")
    policies=("simulator_trained_mlp","unknown_first_then_oldest","first_registered")
    report={p:{"agreements":0,"disagreements":0,"known_selected_outcomes":0,
               "unknown_alternative_outcomes":0,"recommendations":[]} for p in policies}
    prev_seq=0
    prev_tick=-1
    for row in rows:
        if (row.get("run_id")!=dataset["run_id"] or
            type(row.get("sequence"))!=int or row["sequence"]!=prev_seq+1 or
            type(row.get("decision_tick"))!=int or row["decision_tick"]<prev_tick):
            raise ValueError("Non-chronological or cross-run event")
        prev_seq=row["sequence"]
        prev_tick=row["decision_tick"]
        if (row.get("unselected_outcomes")!="UNKNOWN"
            or row.get("counterfactual_reward") is not None
            or row.get("optimal_action_label") is not None
            or row.get("new_action_authority") is not False
            or row.get("policy")!="LEAST_RECENTLY_SAMPLED"):
            raise ValueError("Data contains unauthorized counterfactual claims")
        history=row["candidate_history_before_choice"]
        candidates=[x["source"] for x in history]
        if not 1<=len(candidates)<=SOURCES or len(set(candidates))!=len(candidates):
            raise ValueError("Invalid source candidates")
        if row["selected"] not in candidates:
            raise ValueError("Recorded choice not offered")
        outcome=row["selected_outcome"]
        if outcome["status"] not in ("OBSERVED","UNOBSERVED"):
            raise ValueError("Unrecognized observation")
        for name in policies:
            chosen=recommend(history,model,name)
            agreed=chosen==row["selected"]
            entry=report[name]
            entry["agreements"]+=int(agreed)
            entry["disagreements"]+=int(not agreed)
            if agreed and outcome["status"]=="OBSERVED":
                entry["known_selected_outcomes"]+=1
            if not agreed:
                entry["unknown_alternative_outcomes"]+=1
            entry["recommendations"].append({
                "sequence":row["sequence"],"decision_tick":row["decision_tick"],
                "recommended":chosen,"recorded":row["selected"],
                "agreed":agreed,
                "outcome_evaluable":agreed and outcome["status"]=="OBSERVED",
                "alternative_outcome":"UNKNOWN" if not agreed else "NOT_APPLICABLE"
            })
    result={
        "schema":SCHEMA,"origin":"REAL_FORGE_OFFLINE_SHADOW",
        "run_id":dataset["run_id"],
        "source_file_sha256":dataset["source_file_sha256"],
        "input_experience_sha256":dataset.get("sha256"),
        "real_decisions":len(rows),
        "policy_training_origin":"SIMULATED_ONLY",
        "mlp_training_seed":11,"mlp_training_episodes":500,
        "mlp_transfer_calibration":"UNVALIDATED_100_TICK_AGE_SCALING",
        "recorded_policy":"LEAST_RECENTLY_SAMPLED",
        "reward_comparison_performed":False,
        "counterfactual_outcomes_inferred":False,
        "minecraft_actions_authorized":False,
        "policies":report
    }
    for name in policies:
        report[name]["agreement_rate"]=round(report[name]["agreements"]/len(rows),6)
    canonical=json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)
    result["sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("experience",type=Path)
    p.add_argument("--output",type=Path,default=Path("real-attention-shadow.json"))
    args=p.parse_args()
    model=train_synthetic(11,500)
    data=json.loads(args.experience.read_text())
    result=compare(data,model)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    for name,entry in result["policies"].items():
        print("REAL_ATTENTION_SHADOW",name,"agreement="+str(entry["agreement_rate"]),
              "unobserved_alternatives="+str(entry["unknown_alternative_outcomes"]))
    print("REAL_ATTENTION_SHADOW_COMPLETE reward_comparison=false actions=false")

if __name__=="__main__":
    main()
