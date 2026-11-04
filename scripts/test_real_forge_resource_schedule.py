#!/usr/bin/env python3
"""Pure schedule plan, determinism, and real receipt-validation contracts."""
from real_forge_resource_schedule import plan,command,validate_log,MAX_STEPS

def reject(fn):
    try:fn()
    except ValueError:return
    raise AssertionError("invalid schedule evidence accepted")

def main():
    a=plan("world-A")
    assert a==plan("world-A")
    b=plan("world-B")
    assert a["sha256"]!=b["sha256"]
    assert len(a["steps"])==MAX_STEPS
    assert len({s["source"] for s in a["steps"]})==2
    assert all(s["wheat"] in range(5) for s in a["steps"])
    counts=dict(a["initial_wheat"])
    for s in a["steps"]:
        assert counts[s["source"]]!=s["wheat"]
        counts[s["source"]]=s["wheat"]
        assert "data merge block " in command(s)
    reject(lambda:plan("world-A","unknown"))
    reject(lambda:plan("world-A\n"))
    def report():
        previous=50
        events=[]
        for step in a["steps"]:
            before=previous+1
            after=before+2
            events.append(dict(index=step["index"],source=step["source"],
                               wheat=step["wheat"],tick_before=before,
                               tick_after=after,status="RCON_MODIFIED"))
            previous=after
        return {"schema":a["schema"],"origin":"REAL_FORGE_RCON",
                "configured_world_seed":"world-A","schedule_sha256":a["sha256"],
                "executions":events,"counterfactual_outcomes_inferred":False}
    observed=report()
    assert validate_log(observed)["verified_interventions"]==MAX_STEPS
    observed["executions"][1]["tick_before"]=-1
    reject(lambda:validate_log(observed))
    observed=report()
    observed["schedule_sha256"]="wrong"
    reject(lambda:validate_log(observed))
    observed=report()
    observed["executions"][2]["status"]="SUCCESS_ASSUMED"
    reject(lambda:validate_log(observed))
    print("FORGE_SEEDED_RESOURCE_SCHEDULE_TESTS_PASS")

if __name__=="__main__":
    main()
