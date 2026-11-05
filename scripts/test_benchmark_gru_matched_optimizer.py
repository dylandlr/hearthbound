#!/usr/bin/env python3
"""Matched GRU optimizer counts, truncated gradient and privacy contracts."""
import math
import numpy as np
from benchmark_gru_matched_optimizer import (
    buffered_one_step_gradients,train,update,replay,benchmark,WINDOW,ARMS)
from benchmark_gru_truncated_bptt import sequence_gradients
from benchmark_recurrent_causal_attention import GRU,HIDDEN,INPUT
from benchmark_frozen_attention_timelines import make_timeline

def rejected(fn):
    try:fn()
    except ValueError:return
    raise AssertionError("invalid gradient or benchmark accepted")

def main():
    model=GRU(72)
    rng=np.random.default_rng(23)
    hidden=np.zeros(HIDDEN)
    caches=[];actions=[];rewards=[]
    for i in range(WINDOW):
        inp=rng.normal(0,.1,INPUT)
        _,hidden,c=model.step(inp,hidden)
        caches.append(c);actions.append(i%4);rewards.append(float(i%2))
    one=buffered_one_step_gradients(model,caches,actions,rewards)
    manual={name:np.zeros_like(value) for name,value in model.params.items()}
    for cache,action,reward in zip(caches,actions,rewards):
        g=model.gradients(cache,action,reward)
        for key in manual:manual[key]+=g[key]
    for key in one:
        assert np.array_equal(one[key],manual[key])
    temporal=sequence_gradients(model,caches,actions,rewards)
    assert any(np.max(np.abs(one[key]-temporal[key]))>1e-8
               for key in ("Uz","Ur","Un","Wz","Wr","Wn"))
    rejected(lambda:buffered_one_step_gradients(model,[],[],[]))
    rejected(lambda:buffered_one_step_gradients(model,caches,actions[:-1],rewards))
    rejected(lambda:update(model,one,0))
    one_model,n0=train(14,8,False)
    bptt_model,n8=train(14,8,True)
    assert n0==n8==8*4
    assert any(not np.array_equal(one_model.params[k],bptt_model.params[k])
               for k in one_model.params)
    timeline=make_timeline(788,"unequal_volatility",4)
    result=replay(timeline,{"one_step_buffered":one_model,
                            "eight_step_bptt":bptt_model})
    assert set(result)==set(ARMS)
    assert all(0<=v["direct_discoveries"]<=32 for v in result.values())
    small=benchmark((3,5,7),8,2)
    assert small==benchmark((3,5,7),8,2)
    assert len(small["cases"])==36
    assert small["same_update_cadence"] is True
    assert small["same_initial_weights"] is True
    assert small["training_action_histories_guaranteed_identical"] is False
    assert small["heldout_latent_timelines_shared"] is True
    assert small["minecraft_model_promotion_authorized"] is False
    rejected(lambda:benchmark((3,3,7),8,2))
    rejected(lambda:benchmark((3,5,7),0,2))
    print("GRU_MATCHED_OPTIMIZER_UPDATES_AND_HISTORY_ONLY_CONTRACT_PASS")

if __name__=="__main__":
    main()
