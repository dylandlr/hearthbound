#!/usr/bin/env python3
"""GRU gate derivatives, privacy, deterministic frozen replay and no promotion."""
import math
import numpy as np
from benchmark_recurrent_causal_attention import (
    GRU,INPUT,HIDDEN,history_input,train,replay,benchmark)
from benchmark_frozen_attention_timelines import FrozenWorld,make_timeline
from benchmark_exploration_aware_attention import train_exploration

def refused(fn):
    try:fn()
    except ValueError:return
    raise AssertionError("invalid recurrent input accepted")

def main():
    model=GRU(11)
    rng=np.random.default_rng(41)
    x=rng.normal(0,.15,INPUT)
    h=rng.normal(0,.1,HIDDEN)
    output,next_h,cache=model.step(x,h)
    assert output.shape==(4,) and next_h.shape==(HIDDEN,)
    grads=model.gradients(cache,2,.7)
    # Finite-difference check: recurrent gate gradients must be real, not an
    # untrained random reservoir with only the output projection fitted.
    for key,index in (("Wz",(0,0)),("Uz",(1,1)),("Wr",(0,3)),
                      ("Ur",(2,2)),("Wn",(3,4)),("Un",(0,0)),
                      ("bz",(0,)),("br",(2,)),("bn",(1,)),
                      ("Wo",(2,0)),("bo",(2,))):
        param=model.params[key]
        old=param[index]
        eps=1e-5
        def loss():
            q=model.step(x,h)[0][2]
            return .5*(q-.7)**2
        param[index]=old+eps
        plus=loss()
        param[index]=old-eps
        minus=loss()
        param[index]=old
        assert math.isclose(grads[key][index],(plus-minus)/(2*eps),
                            abs_tol=2e-7,rel_tol=1e-4),(key,index)
    refused(lambda:model.step([0.]*15,[0.]*HIDDEN))
    refused(lambda:model.step([0.]*INPUT,[0.]*10))
    refused(lambda:model.gradients(cache,4,.5))
    t=make_timeline(888,"unequal_volatility",2)
    world=FrozenWorld(t)
    assert history_input(world,None,0,0).shape==(INPUT,)
    assert all(world.features()[i*4]==1. for i in range(4))
    world.inspect(2)
    assert all(world.features()[i*4]==1. for i in (0,1,3))
    m=train(7,8)
    mlp=train_exploration(7,8)
    result=replay(t,m,mlp)
    assert result==replay(t,m,mlp)
    assert all(0<=x["direct_discoveries"]<=32 for x in result.values())
    small=benchmark((3,5,7),8,2)
    assert small==benchmark((3,5,7),8,2)
    assert len(small["cases"])==36
    assert small["architecture"]["training_gradient"]=="ONE_STEP_TRUNCATED_RECURRENT_GATE_GRADIENT"
    assert small["matched_hidden_trajectories_per_episode"] is True
    assert small["policy_can_read_future_timeline"] is False
    assert small["training_uses_unselected_source_rewards"] is False
    assert small["minecraft_model_promotion_authorized"] is False
    refused(lambda:benchmark((3,3,7),8,2))
    refused(lambda:benchmark((3,5,7),0,2))
    print("RECURRENT_CAUSAL_ATTENTION_GRADIENT_AND_PRIVACY_CONTRACT_PASS")

if __name__=="__main__":
    main()
