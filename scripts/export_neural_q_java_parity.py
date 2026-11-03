#!/usr/bin/env python3
"""Export a frozen simulator-trained checkpoint to a strict Java-readable format.

No model is allowed to run Minecraft actions. Fixture predictions are generated
in Python and tested against a *separately implemented* Java evaluator.
"""
import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from train_simulated_mill_neural_q import (
    ACTIONS, FEATURES, SCHEMA, WIDTH, HIDDEN, canonical, load_checkpoint
)

MODEL_HEADER="hearthbound.simulated-neural-q-java-parity.v1"

def export(checkpoint_path, weights_path, fixtures_path):
    checkpoint=json.loads(checkpoint_path.read_text())
    model=load_checkpoint(checkpoint)
    payload=checkpoint["payload"]
    weights=payload["weights"]
    fmt=lambda v: format(v,".17g")
    weights_lines=[
        MODEL_HEADER,
        "observation_schema="+SCHEMA,
        "features="+",".join(FEATURES),
        "actions="+",".join(ACTIONS),
        f"dimensions={WIDTH},{HIDDEN},{len(ACTIONS)}",
        "checkpoint_sha256="+checkpoint["sha256"],
    ]
    for name in ("w1","b1","w2","b2"):
        raw=weights[name]
        nums=[v for row in raw for v in row] if name.startswith("w") else raw
        weights_lines.append(name+"="+",".join(fmt(n) for n in nums))
    weights_path.write_text("\n".join(weights_lines)+"\n")

    # Fixture construction never provides scripted action labels to the model.
    states=[
        ("unknown", (1.,0.,0.,0.,0.,1.,0.,0.,0.,0.)),
        ("empty", (1.,0.,0.,0.,0.,0.,1.,0.,0.,0.)),
        ("available", (1.,0.,0.,0.,0.,0.,0.,1.,0.,0.)),
        ("stale", (1.,0.,0.,0.,0.,1.,0.,0.,0.,1.)),
        ("busy", (1.,0.,0.,0.,0.,0.,0.,1.,1.,0.)),
        ("unpowered", (0.,0.,0.,0.,0.,1.,0.,0.,0.,0.)),
        ("processing", (1.,1.,0.,0.,0.,0.,0.,1.,1.,0.)),
        ("flour", (1.,0.,1.,0.,0.,0.,0.,1.,0.,0.)),
    ]
    rng=random.Random(7001)
    for i in range(40):
        source=rng.randrange(3)
        x=[float(rng.randrange(2)) for _ in range(10)]
        x[4]=rng.randrange(11)/10.0
        x[5:8]=[float(j==source) for j in range(3)]
        states.append((f"random_{i:02}",tuple(x)))
    fixtures=[ "hearthbound.simulated-neural-q-parity-fixtures.v1",
               "checkpoint_sha256="+checkpoint["sha256"] ]
    for label,x in states:
        q=model.values(x)[2]
        choice=max(range(len(q)),key=lambda i:q[i])
        fixtures.append(label+"|"+",".join(fmt(v) for v in x)
                        +"|"+",".join(fmt(v) for v in q)+"|"+str(choice))
    fixtures_path.write_text("\n".join(fixtures)+"\n")
    return len(states)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("checkpoint",type=Path)
    p.add_argument("--weights",type=Path,default=Path("neural-q-java-weights.txt"))
    p.add_argument("--fixtures",type=Path,default=Path("neural-q-java-fixtures.txt"))
    args=p.parse_args()
    count=export(args.checkpoint,args.weights,args.fixtures)
    print(f"SIMULATED_ONLY_NEURAL_Q_PARITY_FIXTURES {count}")

if __name__=="__main__":
    main()
