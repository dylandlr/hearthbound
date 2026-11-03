#!/usr/bin/env python3
"""Extract audited, read-only policy comparisons from genuine Minecraft RCON logs.

Parser self-tests use synthetic text; production evidence requires CI server logs.
"""
import argparse
import json
import pathlib
import re

REQUIRED = {
    "empty_powered": "REQUEST_WHEAT_HAUL",
    "output_ready": "COLLECT_OUTPUT",
    "citizen_experienced": "COLLECT_OUTPUT",
}
PAIR = re.compile(r"LIVE_SHADOW_PAIR stage=(\w+) expected=(\w+) scripted=(POLICY_PROBE .*?) trained=(POLICY_PROBE .*)")
def field(line, name):
    match = re.search(r"(?:^|\s)" + re.escape(name) + r"=([^\s]+)", line)
    if not match:
        raise ValueError("Missing " + name)
    return match.group(1)
def analyze(text):
    found = {}
    for line in text.splitlines():
        match = PAIR.search(line)
        if not match: continue
        stage, expected, scripted, trained = match.groups()
        if stage not in REQUIRED or stage in found:
            raise ValueError("Unexpected or duplicated shadow stage " + stage)
        if expected != REQUIRED[stage]:
            raise ValueError("Expected action mismatch on " + stage)
        if field(scripted,"shadow_mode") != "SCRIPTED":
            raise ValueError("Scripted mode mismatch")
        if field(trained,"shadow_mode") != "TRAINED_MLP":
            raise ValueError("Trained mode mismatch")
        for output in (scripted, trained):
            if field(output,"selected_action") != expected:
                raise ValueError("Policy action mismatch on " + stage)
            if "EXECUTION_DISABLED" not in output:
                raise ValueError("Shadow policy permitted execution")
        for key in ("citizen", "pos", "powered", "wheat", "flour", "blocked", "experience"):
            if field(scripted,key) != field(trained,key):
                raise ValueError("Policies saw different " + key + " on " + stage)
        if stage == "citizen_experienced" and field(trained,"experience") != "1":
            raise ValueError("Citizen experience not observed")
        found[stage] = {
            "scripted": field(scripted,"selected_action"),
            "trained": field(trained,"selected_action"),
            "raw_model": field(trained,"mlp_action"),
            "disagreement": field(trained,"model_disagreement") == "true",
            "masked": field(trained,"action_masked") == "true",
            "experience": int(field(trained,"experience")),
            "powered": field(trained,"powered") == "true",
        }
    missing=set(REQUIRED)-set(found)
    if missing:
        raise ValueError("Missing real Minecraft shadow states: "+", ".join(sorted(missing)))
    return {
        "schema":"hearthbound.live-shadow-evidence.v1",
        "source":"RCON responses from real Forge dedicated-server smoke",
        "read_only":True,
        "stages":found,
        "disagreements":sum(x["disagreement"] for x in found.values()),
        "masked":sum(x["masked"] for x in found.values()),
        "learning_improvement_demonstrated":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("log",type=pathlib.Path)
    p.add_argument("--output",type=pathlib.Path,default=pathlib.Path("live-shadow-report.json"))
    a=p.parse_args()
    report=analyze(a.log.read_text(encoding="utf-8",errors="replace"))
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()
