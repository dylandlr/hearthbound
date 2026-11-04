#!/usr/bin/env python3
"""No event-level pseudoreplication and no fabricated reward in run aggregates."""
import hashlib
import json
import tempfile
from pathlib import Path

from aggregate_real_attention_runs import aggregate,canonical
from evaluate_real_attention_shadow import compare
from evaluate_causal_attention_history import train
from test_evaluate_real_attention_shadow import fixture

def fake(path,run_id,model,decisions=3):
    data=fixture()
    data["run_id"]=run_id
    data["records"]=decisions
    data["transitions"]=data["transitions"][:decisions]
    for n,row in enumerate(data["transitions"],1):
        row["run_id"]=run_id
        row["sequence"]=n
    report=compare(data,model)
    path.write_text(json.dumps(report,sort_keys=True)+"\n")
    return report

def denied(paths):
    try:aggregate(paths)
    except ValueError:return
    raise AssertionError("invalid run dataset accepted")

def main():
    model=train(7,12)
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary)
        a=root/"a.json"
        b=root/"b.json"
        run1="11111111-1111-4111-8111-111111111111"
        run2="22222222-2222-4222-8222-222222222222"
        fake(a,run1,model,3)
        fake(b,run2,model,2)
        result=aggregate([a,b])
        assert result==aggregate([b,a]), "ordering of input files must not matter"
        assert result["distinct_run_ids"]==2
        assert result["unit_of_analysis"]=="RUN"
        assert result["independence_verified"] is False
        assert result["generalization_claim_allowed"] is False
        assert result["statistical_significance_claimed"] is False
        assert result["reward_comparison_performed"] is False
        assert result["minecraft_actions_authorized"] is False
        for name,metrics in result["policies"].items():
            assert metrics["run_count"]==2
            assert 0<=metrics["unweighted_mean_run_agreement_rate"]<=1
            assert metrics["total_agreements_descriptive_only"]<=5
            assert metrics["total_unknown_alternatives"]<=5
        denied([a,a])
        denied([])
        corrupted=json.loads(b.read_text())
        corrupted["run_id"]=run1
        b.write_text(json.dumps(corrupted))
        denied([a,b])
        fake(b,run2,model,2)
        corrupted=json.loads(b.read_text())
        corrupted["reward_comparison_performed"]=True
        b.write_text(json.dumps(corrupted))
        denied([a,b])
        fake(b,run2,model,2)
        corrupted=json.loads(b.read_text())
        corrupted["policies"]["simulator_trained_mlp"]["unknown_alternative_outcomes"]+=1
        corrupted.pop("sha256")
        corrupted["sha256"]=hashlib.sha256(canonical(corrupted).encode()).hexdigest()
        b.write_text(json.dumps(corrupted))
        denied([a,b])
    print("ATTENTION_RUN_LEVEL_AGGREGATION_TESTS_PASS")

if __name__=="__main__":
    main()
