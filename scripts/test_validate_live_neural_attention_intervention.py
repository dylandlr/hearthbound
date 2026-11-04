#!/usr/bin/env python3
"""Contracts for live Forge neural intervention evidence; synthetic fixtures only."""
import json
from real_forge_resource_schedule import plan
from validate_live_neural_attention_intervention import validate

RUN="11111111-1111-4111-8111-111111111111"
def evidence():
    seed="probe-A"
    a=plan(seed)
    events=[]
    t=100
    for s in a["steps"]:
        events.append(dict(index=s["index"],source=s["source"],wheat=s["wheat"],
                           tick_before=t,tick_after=t+1,status="RCON_MODIFIED"))
        t+=20
    schedule={"schema":a["schema"],"origin":"REAL_FORGE_RCON",
              "configured_world_seed":seed,"schedule_sha256":a["sha256"],
              "measurement_stop_tick":t+20,"executions":events,
              "counterfactual_outcomes_inferred":False}
    def row(tick,policy):
        return {"run_id":RUN,"decision_tick":tick,
                "policy":policy,"selected":"9,100,2",
                "candidate_history_before_choice":[{"source":"9,100,2"},{"source":"10,100,2"}],
                "selected_outcome":{"status":"OBSERVED"},
                "unselected_outcomes":"UNKNOWN","counterfactual_reward":None,
                "optimal_action_label":None,"new_action_authority":False}
    experience={"schema":"hearthbound.verified-citizen-experience.v1",
                "origin":"VERIFIED_REAL_FORGE_ATTENTION_JOURNAL",
                "source_finalized":True,"learning_performed":False,
                "training_labels_inferred":False,"minecraft_actions_authorized":False,
                "run_id":RUN,"records":3,
                "transitions":[row(85,"LEAST_RECENTLY_SAMPLED"),
                               row(108,"NEURAL_CAUSAL_MLP_OPT_IN"),
                               row(120,"NEURAL_CAUSAL_MLP_OPT_IN")]}
    return experience,schedule

def denied(x,s):
    try:validate(x,s)
    except ValueError:return
    raise AssertionError("Invalid neural experiment accepted")

def main():
    x,s=evidence()
    a=validate(x,s)
    assert a["neural_selected_inspections"]==2
    assert a["selected_outcome_counts"]["OBSERVED"]==2
    assert a["scripted_selections_inside_window"]==0
    assert a["neural_policy_outperformed_scripted"] is None
    assert a["counterfactual_rewards_inferred"] is False
    assert a==validate(x,s)
    y=json.loads(json.dumps(x))
    y["transitions"][1]["policy"]="LEAST_RECENTLY_SAMPLED"
    denied(y,s)
    y=json.loads(json.dumps(x))
    y["transitions"][1]["selected"]="11,100,2"
    denied(y,s)
    y=json.loads(json.dumps(x))
    y["transitions"][1]["counterfactual_reward"]=1.
    denied(y,s)
    y=json.loads(json.dumps(x))
    y["transitions"][1]["policy"]="UNKNOWN"
    denied(y,s)
    y=json.loads(json.dumps(x))
    y["transitions"][1]["decision_tick"]=s["measurement_stop_tick"]+1
    y["transitions"][2]["decision_tick"]=s["measurement_stop_tick"]+2
    denied(y,s)
    wrong=json.loads(json.dumps(s))
    wrong["schedule_sha256"]="invalid"
    denied(x,wrong)
    print("LIVE_FORGE_NEURAL_INTERVENTION_TESTS_PASS")

if __name__=="__main__":
    main()
