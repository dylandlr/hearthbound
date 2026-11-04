#!/usr/bin/env python3
"""Seeded Forge arms are comparable only with verified, matched metadata."""
import hashlib
import json
from report_seeded_forge_arm_pair import summarize

def arm(policy,run_id,seed="seed-A",schedule="a"*64,count=2):
    world={"schema":"hearthbound.real-forge-world-provenance.v1",
           "origin":"FORGE_SERVER_PROPERTIES_CAPTURE",
           "fixture_id":"chest-two-source-seeded-v1",
           "world_generation_verified":False,
           "independent_world_sample_claimed":False,
           "neural_policy_executed":False,
           "policy_arm":policy,"world_seed_configured":seed}
    result={"schema":"hearthbound.forge-intervention-observation-coverage.v1",
            "origin":"REAL_FORGE_RCON_AND_FINALIZED_JOURNAL",
            "configured_world_seed":seed,
            "run_id":run_id,"schedule_sha256":schedule,
            "interventions_verified":6,
            "explicit_measurement_window":True,
            "measurement_stop_tick":360,
            "interventions_with_matching_direct_observation":count,
            "interventions_without_matching_direct_observation":6-count,
            "observational_coverage_rate":round(count/6,6),
            "counterfactual_outcomes_inferred":False,
            "learning_or_policy_superiority_claimed":False,
            "minecraft_actions_authorized":False,
            "journal_sha256":"b"*64}
    unsigned=json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)
    result["sha256"]=hashlib.sha256(unsigned.encode()).hexdigest()
    return world,result

def denied(pairs):
    try:summarize(pairs)
    except ValueError:return
    raise AssertionError("invalid seeded Forge pair accepted")

def main():
    scripted=arm("SCRIPTED","11111111-1111-4111-8111-111111111111")
    trained=arm("TRAINED_MLP","22222222-2222-4222-8222-222222222222",count=4)
    a=summarize([scripted,trained])
    assert a==summarize([trained,scripted])
    assert not a["independent_world_samples"]
    assert not a["policy_superiority_claimed"]
    assert not a["neural_attention_execution_verified"]
    assert len(a["arms"])==2
    denied([scripted,scripted])
    denied([scripted,arm("TRAINED_MLP",scripted[1]["run_id"])])
    denied([scripted,arm("TRAINED_MLP","33333333-3333-4333-8333-333333333333",seed="seed-B")])
    denied([scripted,arm("TRAINED_MLP","33333333-3333-4333-8333-333333333333",schedule="z"*64)])
    forged=json.loads(json.dumps(trained))
    forged[1]["interventions_with_matching_direct_observation"]=5
    denied([scripted,forged])
    forged=json.loads(json.dumps(trained))
    forged[1]["explicit_measurement_window"]=False
    denied([scripted,forged])
    forged=json.loads(json.dumps(trained))
    forged[0]["independent_world_sample_claimed"]=True
    denied([scripted,forged])
    print("SEEDED_FORGE_MATCHED_ARM_REPORT_CONTRACT_PASS")

if __name__=="__main__":
    main()
