#!/usr/bin/env python3
"""Aggregate authoritative Minecraft experiment output without inventing success."""
import argparse, json, pathlib, re, datetime

def summarize(log, scenario, seed, exit_code):
    text=pathlib.Path(log).read_text(errors="replace") if pathlib.Path(log).exists() else ""
    events={}
    patterns={
        "autonomous_request":r"HEARTHBOUND_AUTONOMOUS_REQUEST",
        "autonomous_teaching":r"HEARTHBOUND_AUTONOMOUS_TEACH",
        "create_callbacks":r"HEARTHBOUND_PROCESS_CALLBACK",
        "verified_receipts":r"HEARTHBOUND_PROCESS_RECEIPT",
        "research_awards":r"HEARTHBOUND_RESEARCH_AWARD job=",
        "hypotheses_confirmed":r"HEARTHBOUND_HYPOTHESIS_EVIDENCE[^\n]*status=CONFIRMED",
        "rejected_receipts":r"HEARTHBOUND_PROCESS_REJECT",
    }
    for name,pattern in patterns.items(): events[name]=len(re.findall(pattern,text))
    return {
        "schema_version":1,"scenario":scenario,"seed":seed,
        "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "exit_code":exit_code,"passed":exit_code==0,
        "events":events,
        "source":"dedicated Forge server logs",
        "limitations":"Counts are log-derived. They do not replace scenario assertions or confirm video rendering."
    }
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--log",required=True)
    p.add_argument("--scenario",required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--exit-code",type=int,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    path=pathlib.Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(summarize(a.log,a.scenario,a.seed,a.exit_code),indent=2)+"\n")
    print(path.read_text())
