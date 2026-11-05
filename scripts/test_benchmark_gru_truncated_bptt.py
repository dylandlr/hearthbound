#!/usr/bin/env python3
"""Finite differences for real recurrent temporal credit and evidence hygiene."""
import math
import numpy as np
from benchmark_gru_truncated_bptt import (
    sequence_gradients,train_bptt,benchmark,evaluate_one,WINDOW)
from benchmark_recurrent_causal_attention import GRU,INPUT,HIDDEN
from benchmark_frozen_attention_timelines import make_timeline

def rejected(fn):
    try:fn()
    except ValueError:return
    raise AssertionError("invalid recurrent sequence accepted")

def main():
    m=GRU(4)
    rng=np.random.default_rng(678)
    xs=[rng.normal(0,.15,INPUT) for _ in range(4)]
    actions=[1,2,0,3]
    rewards=[0.,1.,1.,0.]
    hidden=np.zeros(HIDDEN)
    caches=[]
    for x in xs:
        _,hidden,c=m.step(x,hidden)
        caches.append(c)
    g=sequence_gradients(m,caches,actions,rewards)
    def loss():
        h=np.zeros(HIDDEN)
        total=0.
        for x,action,reward in zip(xs,actions,rewards):
            scores,h,_=m.step(x,h)
            total+=.5*(float(scores[action])-reward)**2
        return total
    for name,idx in (
        ("Wz",(0,0)),("Uz",(1,2)),("bz",(0,)),
        ("Wr",(2,4)),("Ur",(1,3)),("br",(1,)),
        ("Wn",(3,5)),("Un",(2,2)),("bn",(4,)),
        ("Wo",(1,0)),("bo",(2,))):
        original=m.params[name][idx]
        eps=1.e-5
        m.params[name][idx]=original+eps
        plus=loss()
        m.params[name][idx]=original-eps
        minus=loss()
        m.params[name][idx]=original
        assert math.isclose(g[name][idx],(plus-minus)/(2*eps),
                            rel_tol=3e-4,abs_tol=5e-7),(name,idx)
    # Crucial BPTT requirement: the loss at a LATER decision must
    # affect an earlier time step's hidden-state/gate parameters.
    earlier_only=m.gradients(caches[0],actions[0],rewards[0])
    assert any(np.max(np.abs(g[name]-earlier_only[name]))>1e-8
               for name in ("Wz","Uz","Wn","Un","Wr","Ur"))
    rejected(lambda:sequence_gradients(m,[],[],[]))
    rejected(lambda:sequence_gradients(m,caches,actions[:-1],rewards))
    rejected(lambda:sequence_gradients(m,caches,[0,1,2,4],rewards))
    rejected(lambda:train_bptt(7,4,window=3))
    rejected(lambda:train_bptt(7,0))
    trained=train_bptt(13,8)
    t=make_timeline(777,"unequal_volatility",4)
    result=evaluate_one(t,{"one_step_gru":m,"tbptt_gru":trained})
    assert set(result)=={"scripted","one_step_gru","tbptt_gru"}
    assert all(0<=v["direct_discoveries"]<=32 for v in result.values())
    out=benchmark((3,5,7),8,2)
    assert out==benchmark((3,5,7),8,2)
    assert len(out["cases"])==36
    assert out["bptt_window"]==WINDOW
    assert out["gradient"]=="TRUNCATED_BPTT_THROUGH_RECURRENT_HIDDEN_STATE"
    assert out["fixed_trajectory_controls"] is True
    assert out["policy_sees_hidden_source_truth"] is False
    assert out["minecraft_model_promotion_authorized"] is False
    print("GRU_TRUNCATED_BPTT_FULL_TEMPORAL_GRADIENT_CONTRACT_PASS")

if __name__=="__main__":
    main()
