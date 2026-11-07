#!/usr/bin/env python3
"""Generate independent Python float64 inference fixtures for Java parity.

Only frozen model bytes and simulated report features enter this test.
No Minecraft observations or physical-world outcome labels are read.
"""
import argparse
import hashlib
import math
import random
from pathlib import Path

from train_report_choice_mlp import make_sample

def parse(line, key, count):
    if not line.startswith(key + "="):
        raise AssertionError("Malformed model field " + key)
    vals = [float(x) for x in line.split("=",1)[1].split(",")]
    if len(vals) != count or not all(math.isfinite(x) for x in vals):
        raise AssertionError("Bad weight tensor " + key)
    return vals

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--sha", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    data = args.model.read_bytes()
    if hashlib.sha256(data).hexdigest() != args.sha.read_text().strip():
        raise AssertionError("Frozen model changed before parity")
    lines = data.decode("utf-8").strip().splitlines()
    if len(lines) != 11 or lines[0] != "hearthbound.report-choice-mlp.v1":
        raise AssertionError("Wrong checkpoint")
    w1, b1, w2, b2 = (
        parse(lines[7], "w1", 160), parse(lines[8], "b1", 16),
        parse(lines[9], "w2", 48), parse(lines[10], "b2", 3))
    rng = random.Random(21071107)
    vectors = [make_sample(rng)[0] for _ in range(64)]
    # Explicit hard mask/empty cases and fresh, well-separated source values.
    vectors.extend([
        [0.0]*10,
        [1.0, .375, .02, .02, .0625] + [0.0]*5,
        [0.0]*5 + [1.0, .125, .02, .02, .0625],
        [1.0, .375, .01, .01, .0625, 1.0, .125, .01, .01, .0625],
        [1.0, .125, .8, .8, .0625, 1.0, .375, .01, .01, .0625],
    ])
    rows = ["schema=hearthbound.report-mlp-python-java-parity.v1"]
    for x in vectors:
        hidden = [math.tanh(b1[j]+sum(w1[j*10+k]*x[k] for k in range(10)))
                  for j in range(16)]
        values = [b2[o]+sum(w2[o*16+j]*hidden[j] for j in range(16))
                  for o in range(3)]
        masked = values[:]
        if not x[0]: masked[0] = float("-inf")
        if not x[5]: masked[1] = float("-inf")
        idx = max(range(3), key=lambda a: (masked[a], -a))
        if not x[0] and not x[5]: idx = 2
        row = "\t".join((
            ",".join(format(t, ".17g") for t in x),
            ",".join(format(t, ".17g") for t in values),
            ["SOURCE_A", "SOURCE_B", "ABSTAIN"][idx],
        ))
        rows.append(row)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("PYTHON_FROZEN_MLP_PARITY_FIXTURES",len(vectors),
          "sha256",hashlib.sha256(args.out.read_bytes()).hexdigest())

if __name__ == "__main__":
    main()
