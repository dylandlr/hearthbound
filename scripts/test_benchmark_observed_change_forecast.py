#!/usr/bin/env python3
"""Selected-label forecasting, temporal derivatives, calibration and replay."""
import math
import numpy as np
from benchmark_observed_change_forecast import (
    chosen_supervised_gradient,train,benchmark,history_baseline,
    probe_forecasts,forecast_policy,compare_policies,reliability,WINDOW)
from benchmark_recurrent_causal_attention import GRU,HIDDEN,INPUT
from benchmark_frozen_attention_timelines import make_timeline,FrozenWorld

def rejected(fn):
    try:fn()
    except ValueError:return
    raise AssertionError("accepted invalid selected observation")

def main():
    model=GRU(19)
    rng=np.random.default_rng(240)
    features=[rng.normal(0,.12,INPUT) for _ in range(4)]
    actions=[0,3,1,2]
    targets=[None,1,0,1]
    hidden=np.zeros(HIDDEN)
    caches=[]
    for x in features:
        _,hidden,c=model.step(x,hidden)
        caches.append(c)
    gradients,n=chosen_supervised_gradient(model,caches,actions,targets)
    assert n==3
    def loss():
        h=np.zeros(HIDDEN)
        value=0.
        for x,action,target in zip(features,actions,targets):
            scores,h,_=model.step(x,h)
            if target is not None:
                score=float(scores[action])
                value+=float(np.logaddexp(0.,score)-target*score)
        return value
    for name,index in (
        ("Wz",(0,0)),("Uz",(2,3)),("bz",(0,)),
        ("Wr",(1,5)),("Ur",(4,2)),("br",(2,)),
        ("Wn",(3,2)),("Un",(1,4)),("bn",(1,)),
        ("Wo",(3,0)),("bo",(2,))):
        param=model.params[name]
        original=param[index]
        eps=1.e-5
        param[index]=original+eps
        plus=loss()
        param[index]=original-eps
        minus=loss()
        param[index]=original
        assert math.isclose(gradients[name][index],(plus-minus)/(2*eps),
                            rel_tol=4e-4,abs_tol=7e-7),(name,index)
    # No first-visit supervision, no training labels on unchosen heads.
    null,n0=chosen_supervised_gradient(model,caches,actions,[None]*4)
    assert n0==0
    assert all(np.count_nonzero(v)==0 for v in null.values())
    rejected(lambda:chosen_supervised_gradient(model,caches,actions,[0,1,2,1]))
    rejected(lambda:chosen_supervised_gradient(model,caches,actions[:-1],targets))
    trajectory=make_timeline(444,"unequal_volatility",4)
    world=FrozenWorld(trajectory)
    assert history_baseline(world)==[.5]*4
    assert forecast_policy(world,[.1,.2,.3,.4])==0
    world.inspect(0)
    assert all(world.memory[i]==-1 for i in (1,2,3))
    rejected(lambda:forecast_policy(world,[.1,float("nan"),.3,.4]))
    assert reliability([(.8,.4,1),(.2,.4,0)])["evaluated_reinspection_labels"]==2
    rejected(lambda:reliability([]))
    model,supervised=train(23,8)
    assert supervised>0
    sample=probe_forecasts(trajectory,model,444)
    assert sample==probe_forecasts(trajectory,model,444)
    assert all(y in (0,1) and 0<=p<=1 for p,q,y in sample)
    outcomes=compare_policies(trajectory,model)
    assert outcomes==compare_policies(trajectory,model)
    assert set(outcomes)=={"scripted","forecast_gated"}
    small=benchmark((3,5,7),8,2)
    assert small==benchmark((3,5,7),8,2)
    assert len(small["cases"])==36
    assert small["first_inspections_masked_from_training_and_forecast_metrics"] is True
    assert small["unselected_rewards_or_labels_used"] is False
    assert small["model_deployed_in_minecraft"] is False
    assert small["minecraft_model_promotion_authorized"] is False
    rejected(lambda:benchmark((3,3,7),8,2))
    rejected(lambda:benchmark((3,5,7),8,0))
    print("OBSERVED_CHANGE_GRU_SUPERVISED_FORECAST_GRADIENT_AND_PRIVACY_PASS")

if __name__=="__main__":
    main()
