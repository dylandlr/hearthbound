#!/usr/bin/env python3
"""Check event detection against hidden truth without leaking it to agents."""
import copy
from benchmark_attention_event_latency import (
    analyze_events,replay_observations,benchmark)
from benchmark_forecast_policy_stress import make_stress_timeline
from benchmark_observed_change_forecast import train as train_forecaster

def rejected(call):
    try:call()
    except ValueError:return
    raise AssertionError("invalid event journal was accepted")

def synthetic(states,selected):
    n=len(states)
    t={"states":states}
    journal=[]
    memory=[-1]*4
    for i,source in enumerate(selected):
        old=memory[source]
        now=states[i][source]
        journal.append({"step":i,"selected_source":source,
            "prior_direct_state":old,"observed_state":now,
            "first_inspection":old==-1,
            "direct_disagreement":old!=-1 and old!=now,
            "direct_discovery":old==-1 or old!=now})
        memory[source]=now
    return t,journal

def main():
    # Transition at step 2 is witnessed immediately after a pre-transition
    # inspection; detection delay must be zero.
    t,j=synthetic([[0]*4,[0]*4,[1,0,0,0],[1,0,0,0]], [0,1,0,1])
    a=analyze_events(t,j)
    assert a["latent_transition_count"]==1
    assert a["transitions_witnessed_before_next_change"]==1
    assert a["mean_detection_latency_steps"]==0
    assert a["total_censored_event_delay_steps"]==0
    # Source flips twice between inspections: no difference remains in the
    # final direct observation; neither event can be claimed as witnessed.
    t,j=synthetic([[0]*4,[1,0,0,0],[0]*4,[0]*4],[0,1,1,0])
    a=analyze_events(t,j)
    assert a["latent_transition_count"]==2
    assert a["transitions_witnessed_before_next_change"]==0
    assert a["total_censored_event_delay_steps"]==5  # horizon 4, events t=1,2
    # An initial visit after the transition is not a detected change;
    # it only establishes the baseline.
    t,j=synthetic([[0]*4,[1,0,0,0],[1,0,0,0]], [1,0,1])
    assert analyze_events(t,j)["transitions_witnessed_before_next_change"]==0
    assert analyze_events(t,j)["total_censored_event_delay_steps"]==2
    # Real policy decisions must always arise from private direct observations.
    trajectory=make_stress_timeline(123,"bursty_mutations")
    model,_=train_forecaster(7,8)
    for arm in ("scripted","greedy_forecast","age_blend","coverage_guard"):
        journal=replay_observations(trajectory,model,arm)
        summary=analyze_events(trajectory,journal)
        assert summary["latent_transition_count"]>=0
        assert summary["transitions_witnessed_before_next_change"]<=summary[
            "baseline_eligible_transitions"]
        assert summary["reinspection_count"]+summary[
            "first_inspection_count"]==len(trajectory["states"])
        assert summary["unproductive_reinspections"]>=0
        assert summary["total_censored_event_delay_steps"]>=summary["total_detection_delay_steps"]
        assert all(v["detection_delay_steps"] is None or
            v["detection_delay_steps"]>=0 for v in summary["events"])
        damaged=copy.deepcopy(journal)
        damaged[0]["observed_state"]^=1
        rejected(lambda:analyze_events(trajectory,damaged))
    result=benchmark((3,5,7),8,2)
    assert result==benchmark((3,5,7),8,2)
    assert len(result["cells"])==9
    assert result["agent_can_read_hidden_transition_log"] is False
    assert result["event_outcomes_used_for_training"] is False
    assert result["model_promotion_authorized"] is False
    for cell in result["cells"]:
        assert set(cell["mean_by_arm"])=={
            "scripted","greedy_forecast","age_blend","coverage_guard"}
        for arm,metric in cell["paired_against_scripted"].items():
            assert len(metric["witnessed_event_differences"])==2
            assert len(metric["censored_event_delay_differences"])==2
    rejected(lambda:benchmark((3,3,7),8,2))
    print("ATTENTION_EVENT_LATENCY_AND_CAUSAL_ATTRIBUTION_PASS")

if __name__=="__main__":
    main()
