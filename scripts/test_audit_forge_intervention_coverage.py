#!/usr/bin/env python3
"""Distinguish directly witnessed resource states from unobserved interventions."""
import json
import tempfile
from pathlib import Path
from audit_forge_intervention_coverage import audit
from real_forge_resource_schedule import plan
from test_export_verified_citizen_experience import setup
from test_validate_forge_attention_pair import C,O

def fixture(seed="world-A"):
    schedule=plan(seed)
    events=[]
    for i,step in enumerate(schedule["steps"]):
        before=100+i*20
        events.append({"index":step["index"],"source":step["source"],
                       "wheat":step["wheat"],"tick_before":before,
                       "tick_after":before+1,"status":"RCON_MODIFIED"})
    return {"schema":schedule["schema"],"origin":"REAL_FORGE_RCON",
            "configured_world_seed":seed,"schedule_sha256":schedule["sha256"],
            "executions":events,"counterfactual_outcomes_inferred":False}

def selected_pair(tick,source,wheat):
    pos=source.replace(" ",",")
    choice=C.replace("tick=100","tick="+str(tick)).replace("selected=9,100,2","selected="+pos)
    obs=O.replace("tick=100","tick="+str(tick)).replace("selected=9,100,2","selected="+pos)
    state="EMPTY" if wheat==0 else "AVAILABLE"
    obs=obs.replace("state=AVAILABLE","state="+state).replace("wheat=3","wheat="+str(wheat))
    return choice,obs

def denied(schedule,journal,manifest,world=None):
    try:audit(schedule,journal,manifest,world)
    except ValueError:return
    raise AssertionError("invalid intervention coverage accepted")

def main():
    schedule=fixture()
    first=schedule["executions"][0]
    second=schedule["executions"][1]
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        pairs=[
            selected_pair(first["tick_after"]+5,first["source"],first["wheat"]),
            selected_pair(second["tick_after"]+5,second["source"],second["wheat"])
        ]
        journal,manifest=setup(root,pairs)
        report=audit(schedule,journal,manifest)
        assert report==audit(schedule,journal,manifest)
        assert report["interventions_verified"]==6
        assert report["interventions_with_matching_direct_observation"]==2
        assert report["interventions_without_matching_direct_observation"]==4
        assert report["interventions"][0]["witnessed_expected_state"]
        assert report["interventions"][1]["witnessed_expected_state"]
        assert all(not r["witnessed_expected_state"] for r in report["interventions"][2:])
        assert report["counterfactual_outcomes_inferred"] is False
        assert report["learning_or_policy_superiority_claimed"] is False
        assert report["observed_matching_value_is_not_causal_proof"] is True
        wrong=json.loads(json.dumps(schedule))
        wrong["executions"][0]["status"]="ASSUMED"
        denied(wrong,journal,manifest)
        wrong=json.loads(json.dumps(schedule))
        wrong["schedule_sha256"]="forged"
        denied(wrong,journal,manifest)
        wrong=json.loads(json.dumps(schedule))
        world={"schema":"hearthbound.real-forge-world-provenance.v1",
               "origin":"FORGE_SERVER_PROPERTIES_CAPTURE",
               "world_seed_configured":"wrong-seed",
               "fixture_id":"chest-two-source-seeded-v1",
               "world_generation_verified":False}
        denied(wrong,journal,manifest,world)
        # A matching observation recorded during the mutation tick is not
        # attributed to a completed intervention.
        journal,manifest=setup(root,[selected_pair(first["tick_after"],first["source"],first["wheat"])])
        same_tick=audit(schedule,journal,manifest)
        assert same_tick["interventions_with_matching_direct_observation"]==0
    # Explicit cutoff permits witnessing the last intervention, but never
    # events that happen afterward during restart-fixture cleanup.
    schedule=fixture()
    last=schedule["executions"][-1]
    schedule["measurement_stop_tick"]=last["tick_after"]+15
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        timely=selected_pair(last["tick_after"]+5,last["source"],last["wheat"])
        too_late=selected_pair(last["tick_after"]+20,last["source"],last["wheat"])
        journal,manifest=setup(root,[timely,too_late])
        report=audit(schedule,journal,manifest)
        assert report["explicit_measurement_window"] is True
        assert report["measurement_stop_tick"]==last["tick_after"]+15
        assert report["interventions"][-1]["witnessed_expected_state"] is True
        assert report["interventions"][-1]["direct_selected_observations_in_window"]==1
        corrupted=json.loads(json.dumps(schedule))
        corrupted["measurement_stop_tick"]=last["tick_after"]
        denied(corrupted,journal,manifest)
    print("FORGE_INTERVENTION_OBSERVATION_COVERAGE_TESTS_PASS")

if __name__=="__main__":
    main()
