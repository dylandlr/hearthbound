#!/usr/bin/env python3
"""Contract checks for operator-controlled rapid Forge source changes."""
import json
from rapid_four_source_schedule import plan,verify,rcon_command,STEPS,SOURCES

def rejected(fn):
    try:fn()
    except ValueError:return
    raise AssertionError("unsafe rapid-four resource plan/evidence accepted")

def main():
    p=plan("probe-D")
    assert p==plan("probe-D")
    assert p["sha256"]!=plan("probe-E")["sha256"]
    assert len(p["steps"])==STEPS and len(p["sources"])==4
    previous=p["initial_wheat"].copy()
    for event in p["steps"]:
        assert previous[event["source"]]!=event["wheat"]
        previous[event["source"]]=event["wheat"]
        assert "data merge block " in rcon_command(event["source"],event["wheat"])
    rejected(lambda:plan("bad\nseed"))
    rejected(lambda:rcon_command("99 100 2",3))
    ticks=100
    executions=[]
    for event in p["steps"]:
        executions.append({"index":event["index"],"source":event["source"],"wheat":event["wheat"],
                           "tick_before":ticks,"tick_after":ticks+1,"status":"RCON_MODIFIED"})
        ticks+=2
    actual={"schema":"hearthbound.rapid-four-resource-execution.v1",
            "origin":"REAL_FORGE_RCON",
            "configured_world_seed":"probe-D","plan_sha256":p["sha256"],
            "executions":executions,"measurement_stop_tick":ticks+20,
            "counterfactual_outcomes_inferred":False}
    assert verify(actual)["verified_interventions"]==STEPS
    bad=json.loads(json.dumps(actual))
    bad["executions"][3]["status"]="ASSUMED"
    rejected(lambda:verify(bad))
    bad=json.loads(json.dumps(actual))
    bad["executions"][5]["source"]=SOURCES[0]
    rejected(lambda:verify(bad))
    bad=json.loads(json.dumps(actual))
    bad["measurement_stop_tick"]=bad["executions"][-1]["tick_after"]
    rejected(lambda:verify(bad))
    bad=json.loads(json.dumps(actual))
    bad["counterfactual_outcomes_inferred"]=True
    rejected(lambda:verify(bad))
    print("RAPID_FOUR_SOURCE_SCHEDULE_CONTRACT_PASS")

if __name__=="__main__":
    main()
