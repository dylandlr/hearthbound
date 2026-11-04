#!/usr/bin/env python3
"""Freeze causal-history MLP and export reproducible Python/Java score fixtures.

Simulator weights only. Never authorizes Minecraft actions or uses privileged
source-state/true volatility in inference features.
"""
import argparse
import hashlib
import json
import math
import random
from pathlib import Path

from evaluate_causal_attention_history import train
from train_simulated_attention_mlp import WIDTH,HIDDEN,SOURCES

HEADER="hearthbound.causal-attention-mlp-java.v1"
FIXTURE_HEADER="hearthbound.causal-attention-mlp-java-fixtures.v1"
FEATURE_SCHEMA="unknown,last_observed_available,observation_age_norm,empirical_observed_change_rate"

def fmt(value):
    if not math.isfinite(value):raise ValueError("non-finite model value")
    return format(value,".17g")

def flatten(value):
    return [v for row in value for v in row]

def export(weights:Path, fixtures:Path,seed=11,episodes=500):
    model=train(seed,episodes)
    encoded={}
    for name in ("w1","b1","w2","b2"):
        value=getattr(model,name)
        encoded[name]=flatten(value) if name.startswith("w") else list(value)
    lines=[HEADER,"origin=SIMULATED_CAUSAL_HISTORY_ONLY",
           "features="+FEATURE_SCHEMA,
           "dimensions="+str(WIDTH)+","+str(HIDDEN)+","+str(SOURCES),
           "training_seed="+str(seed),"training_episodes="+str(episodes)]
    # Exact digest of the canonical, replayable checkpoint tensor content.
    digest=hashlib.sha256(json.dumps(encoded,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    lines.append("weights_sha256="+digest)
    for name in ("w1","b1","w2","b2"):
        lines.append(name+"="+",".join(map(fmt,encoded[name])))
    weights.write_text("\n".join(lines)+"\n")
    # 4 options × 4 per-option features. 2-4 valid candidates, zero padding.
    # The same fixture cases are independently evaluated by Java.
    rng=random.Random(217)
    result=[FIXTURE_HEADER,"weights_sha256="+digest]
    cases=[
        [1.,0.,1.,.5]*4,
        [0.,1.,0.,0.]*4,
        [0.,0.,.2,.5,1.,0.,1.,.5]+[0.,0.,0.,.5]*2,
    ]
    for _ in range(48):
        count=rng.randint(2,4)
        x=[]
        for i in range(count):
            seen=rng.randrange(2)==1
            x.extend((0. if seen else 1.,rng.choice((0.,1.)) if seen else 0.,
                      rng.randrange(21)/20. if seen else 1.,
                      rng.randrange(11)/10. if seen else .5))
        x.extend([0.,0.,0.,.5]*(4-count))
        cases.append(x)
    for i,x in enumerate(cases):
        scores=model.forward(x)[2]
        # Full-output scoring; padded sources masked at action selection.
        result.append(str(i)+"|"+",".join(map(fmt,x))+"|"+",".join(map(fmt,scores)))
    fixtures.write_text("\n".join(result)+"\n")
    return len(cases)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--weights",type=Path,default=Path("causal-attention-java-weights.txt"))
    ap.add_argument("--fixtures",type=Path,default=Path("causal-attention-java-fixtures.txt"))
    ap.add_argument("--seed",type=int,default=11)
    ap.add_argument("--episodes",type=int,default=500)
    args=ap.parse_args()
    n=export(args.weights,args.fixtures,args.seed,args.episodes)
    print("CAUSAL_ATTENTION_JAVA_FIXTURES count="+str(n)+
          " origin=SIMULATED_ONLY action_authorized=false")

if __name__=="__main__":
    main()
