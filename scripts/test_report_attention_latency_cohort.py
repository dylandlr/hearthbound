#!/usr/bin/env python3
"""Three-run descriptive latency cohort contract tests."""
import hashlib
import json
from report_attention_latency_cohort import cohort
from report_matched_attention_latency import pair,canonical
from test_report_matched_attention_latency import report

def make(i):
    return pair(report("scripted-"+str(i),seed="seed-"+str(i),schedule=chr(97+i)*64),
                report("neural-"+str(i),seed="seed-"+str(i),schedule=chr(97+i)*64,
                       latencies=(6,5,4,3,2,1)))

def resign(item):
    item.pop("sha256",None)
    item["sha256"]=hashlib.sha256(canonical(item).encode()).hexdigest()
    return item

def rejected(items):
    try:cohort(items)
    except ValueError:return
    raise AssertionError("invalid latency cohort accepted")

def main():
    items=[make(i) for i in range(3)]
    output=cohort(items)
    assert output==cohort(list(reversed(items)))
    assert output["configured_seed_pairs"]==3
    assert output["real_server_runs"]==6
    assert output["unweighted_mean_of_pair_differences_ticks"]==0
    assert output["neural_superiority_claimed"] is False
    assert output["identical_intervention_tick_alignment_verified"] is False
    rejected(items[:2])
    rejected([items[0],items[1],items[1]])
    changed=json.loads(json.dumps(items))
    changed[2]["neural_run_id"]=items[0]["neural_run_id"]
    rejected([items[0],items[1],resign(changed[2])])
    changed=json.loads(json.dumps(items))
    changed[2]["mean_descriptive_neural_minus_scripted_latency_ticks"]=4
    rejected([items[0],items[1],resign(changed[2])])
    changed=json.loads(json.dumps(items))
    changed[2]["causal_latency_advantage_claimed"]=True
    rejected([items[0],items[1],resign(changed[2])])
    print("REAL_FORGE_ATTENTION_LATENCY_COHORT_CONTRACT_PASS")

if __name__=="__main__":
    main()
