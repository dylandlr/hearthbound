#!/usr/bin/env python3
"""Audit simulator-only neural abstentions on two measured Minecraft mill states."""
import argparse
import json
import re
from pathlib import Path

STATES={"unpowered":"INSPECT_UNPOWERED","output_ready":"COLLECT_OUTPUT"}
PATTERN=re.compile(
    r"^NEURAL_Q_MILL_CONTEXT arm=(SCRIPTED|TRAINED_MLP)"
    r" stage=(unpowered|output_ready) reference=([A-Z_]+)"
    r" gate=ABSTAIN neural_argmax=([012]) checkpoint=([a-f0-9]{64})"
    r" observation=REAL_MINECRAFT_REPLAY training=SIMULATED_ONLY"
    r" read_only=true dispatch=false$"
)
def parse(log):
    records={}
    hashes=set()
    for line in log.splitlines():
        if "NEURAL_Q_MILL_CONTEXT" not in line:continue
        match=PATTERN.fullmatch(line.strip())
        if match is None:raise ValueError("Invalid or unsafe neural context log")
        arm,state,reference,argmax,digest=match.groups()
        if reference!=STATES[state] or (arm,state) in records:
            raise ValueError("Unexpected reference or duplicate context")
        hashes.add(digest)
        records[(arm,state)]={"reference":reference,"neural_argmax":int(argmax),
                              "gate":"ABSTAIN","task_dispatched":False}
    expected={(arm,state) for arm in ("SCRIPTED","TRAINED_MLP") for state in STATES}
    if set(records)!=expected or len(hashes)!=1:
        raise ValueError("Missing actual-world context coverage or checkpoint mismatch")
    return {
      "schema":"hearthbound.real-mill-context-coverage.v1",
      "origin":"REAL_MINECRAFT_RECORDED_OBSERVATIONS",
      "model_training":"SIMULATED_ONLY",
      "read_only":True,
      "minecraft_learning_claimed":False,
      "gameplay_action_authorized":False,
      "distinct_measured_contexts":2,
      "checkpoint_sha256":next(iter(hashes)),
      "arms":{arm:{state:records[(arm,state)] for state in STATES}
              for arm in ("SCRIPTED","TRAINED_MLP")}
    }
def main():
    p=argparse.ArgumentParser()
    p.add_argument("scripted",type=Path)
    p.add_argument("trained",type=Path)
    p.add_argument("--output",type=Path,default=Path("real-mill-context-coverage.json"))
    args=p.parse_args()
    report=parse(args.scripted.read_text()+"\n"+args.trained.read_text())
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("VERIFIED_REAL_MILL_CONTEXT_COVERAGE",json.dumps(report,sort_keys=True))
if __name__=="__main__":
    main()
