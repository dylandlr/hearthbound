#!/usr/bin/env python3
"""Causal abstention and test fixture contracts for real-attention shadow."""
import json
from evaluate_real_attention_shadow import compare,model_features
from evaluate_causal_attention_history import train

RUN="11111111-1111-4111-8111-111111111111"

def candidate(source,known=False,age=None,count=0):
    return dict(source=source,status="KNOWN" if known else "UNKNOWN",
                last_observed_available=True if known else None,
                last_observed_wheat=3 if known else None,
                age_ticks=age,direct_observation_count=count,
                observed_change_count=0,
                observed_change_rate=0. if count>1 else None)

def fixture():
    rows=[]
    for seq,(selected,history) in enumerate([
        ("9,100,2",[candidate("9,100,2"),candidate("10,100,2")]),
        ("10,100,2",[candidate("9,100,2",True,5,1),candidate("10,100,2")]),
        ("9,100,2",[candidate("9,100,2",True,10,1),candidate("10,100,2",True,5,1)])
    ],1):
        rows.append({
            "run_id":RUN,"sequence":seq,"decision_tick":100+5*seq,
            "policy":"LEAST_RECENTLY_SAMPLED",
            "candidate_history_before_choice":history,"selected":selected,
            "selected_outcome":{"status":"OBSERVED","reason":"VERIFIED",
                "state":"AVAILABLE","wheat":3},
            "unselected_outcomes":"UNKNOWN",
            "counterfactual_reward":None,"optimal_action_label":None,
            "new_action_authority":False
        })
    return {"schema":"hearthbound.verified-citizen-experience.v1",
            "origin":"VERIFIED_REAL_FORGE_ATTENTION_JOURNAL",
            "run_id":RUN,"source_finalized":True,
            "source_file_sha256":"abc","sha256":"def",
            "records":len(rows),"learning_performed":False,
            "training_labels_inferred":False,
            "minecraft_actions_authorized":False,"transitions":rows}

def invalid(d,model):
    try:compare(d,model)
    except ValueError:return
    raise AssertionError("invalid experience was accepted")

def main():
    model=train(3,12)
    d=fixture()
    result=compare(d,model)
    assert result==compare(d,model)
    assert result["real_decisions"]==3
    assert result["policy_training_origin"]=="SIMULATED_ONLY"
    assert result["reward_comparison_performed"] is False
    assert result["counterfactual_outcomes_inferred"] is False
    for name,entry in result["policies"].items():
        assert entry["agreements"]+entry["disagreements"]==3
        assert entry["unknown_alternative_outcomes"]==entry["disagreements"]
        assert all((not r["outcome_evaluable"] or r["agreed"])
                   for r in entry["recommendations"])
        assert all(r["alternative_outcome"]=="UNKNOWN" for r in entry["recommendations"]
                   if not r["agreed"])
    assert len(model_features(d["transitions"][0]["candidate_history_before_choice"]))==16
    for field,value in (
        ("unselected_outcomes","AVAILABLE"),
        ("optimal_action_label","9,100,2"),
        ("counterfactual_reward",1.),
        ("new_action_authority",True),
        ("policy","MODEL_EXECUTED"),
        ("selected","11,100,2")
    ):
        altered=json.loads(json.dumps(d))
        altered["transitions"][0][field]=value
        invalid(altered,model)
    altered=json.loads(json.dumps(d))
    altered["transitions"][1]["decision_tick"]=90
    invalid(altered,model)
    altered=json.loads(json.dumps(d))
    altered["transitions"][0]["candidate_history_before_choice"][0]["last_observed_wheat"]=88
    invalid(altered,model)
    print("REAL_ATTENTION_SHADOW_CONTRACT_PASS")

if __name__=="__main__":
    main()
