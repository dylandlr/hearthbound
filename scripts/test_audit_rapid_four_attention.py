#!/usr/bin/env python3
"""Finalized-journal boundary and single-observer contracts for rapid Forge."""
import json
import tempfile
from pathlib import Path
from rapid_four_source_schedule import plan
from audit_rapid_four_attention import audit
from test_export_verified_citizen_experience import setup
from test_validate_forge_attention_pair import C,O

CANDIDATES="11,100,2;13,100,2;7,100,2;9,100,2"

def execution():
    planned=plan("test-four-fixture")
    rows=[]
    for i,step in enumerate(planned["steps"]):
        tick=100+i*10
        rows.append({"index":step["index"],"source":step["source"],
                     "wheat":step["wheat"],"tick_before":tick,
                     "tick_after":tick+1,"status":"RCON_MODIFIED"})
    return {
        "schema":"hearthbound.rapid-four-resource-execution.v1",
        "origin":"REAL_FORGE_RCON",
        "configured_world_seed":"test-four-fixture",
        "plan_sha256":planned["sha256"],
        "policy":"LEAST_RECENTLY_SAMPLED",
        "model_sha256":None,
        "executions":rows,"measurement_stop_tick":280,
        "counterfactual_outcomes_inferred":False}

def observed(tick,source,wheat,policy="LEAST_RECENTLY_SAMPLED"):
    pos=source.replace(" ",",")
    choice=(C.replace("tick=100","tick="+str(tick))
        .replace("candidates=10,100,2;9,100,2",
                 "candidates="+CANDIDATES)
        .replace("candidate_count=2","candidate_count=4")
        .replace("selected=9,100,2","selected="+pos)
        .replace("policy=LEAST_RECENTLY_SAMPLED","policy="+policy))
    outcome=(O.replace("tick=100","tick="+str(tick))
        .replace("selected=9,100,2","selected="+pos)
        .replace("state=AVAILABLE","state="+("EMPTY" if wheat==0 else "AVAILABLE"))
        .replace("wheat=3","wheat="+str(wheat)))
    return choice,outcome

def rejected(executed,pairs):
    with tempfile.TemporaryDirectory() as tmp:
        journal,manifest=setup(Path(tmp),pairs)
        try:audit(executed,journal,manifest)
        except ValueError:return
    raise AssertionError("invalid four-source witness experiment accepted")

def main():
    record=execution()
    first,second=record["executions"][:2]
    pairs=[observed(105,first["source"],first["wheat"]),
           observed(115,second["source"],second["wheat"])]
    with tempfile.TemporaryDirectory() as tmp:
        journal,manifest=setup(Path(tmp),pairs)
        report=audit(record,journal,manifest)
        assert report==audit(record,journal,manifest)
        assert report["verified_mutations"]==16
        assert report["verified_selected_inspections"]==2
        assert report["witnessed_interventions"]==2
        assert report["unwitnessed_interventions"]==14
        assert report["interventions"][0]["first_witness_latency_ticks"]==4
        assert report["interventions"][1]["first_witness_latency_ticks"]==4
        assert report["counterfactual_outcomes_inferred"] is False
        assert report["claim_of_neural_superiority"] is False
        # A valid journal can be tampered with only by changing the underlying
        # payload, which must fail the sealed-manifest digest.
        journal.write_text(journal.read_text().replace("payload_b64","payload_altered"))
        try:audit(record,journal,manifest)
        except ValueError:pass
        else:raise AssertionError("modified sealed journal accepted")
    rejected(record,[observed(105,first["source"],first["wheat"]),
                     observed(108,second["source"],second["wheat"])])
    rejected(record,[observed(105,first["source"],first["wheat"]),
                     observed(115,second["source"],second["wheat"],
                              "NEURAL_CAUSAL_MLP_OPT_IN")])
    rejected(record,[observed(105,first["source"],first["wheat"]),
                     observed(115,second["source"],second["wheat"])[0:1]+
                     observed(115,second["source"],second["wheat"])[1:]])
    bad=json.loads(json.dumps(record))
    bad["executions"][0]["tick_after"]=280
    rejected(bad,pairs)
    print("RAPID_FOUR_ATTENTION_FINALIZED_JOURNAL_CONTRACT_PASS")

if __name__=="__main__":
    main()
