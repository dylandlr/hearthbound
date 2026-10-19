#!/usr/bin/env python3
"""Aggregate real Forge simulation outputs; never infer passing trials from missing data."""
import argparse, json, pathlib, statistics
p=argparse.ArgumentParser()
p.add_argument("root")
p.add_argument("--output",required=True)
a=p.parse_args()
root=pathlib.Path(a.root)
reports=[]
for path in sorted(root.glob("**/summary.json")):
    record=json.loads(path.read_text())
    if not isinstance(record.get("passed"),bool) or not isinstance(record.get("seed"),int):
        raise ValueError(f"Invalid experiment summary: {path}")
    reports.append(record)
if not reports:
    raise SystemExit("No simulation summaries found; refusing empty benchmark")
keys=sorted(set().union(*(r.get("events",{}).keys() for r in reports)))
aggregate={
    "schema_version":1,
    "trials":len(reports),
    "passed":sum(1 for r in reports if r["passed"]),
    "failed":sum(1 for r in reports if not r["passed"]),
    "success_fraction":sum(1 for r in reports if r["passed"])/len(reports),
    "seeds":[r["seed"] for r in reports],
    "mean_event_counts":{key:statistics.mean(r.get("events",{}).get(key,0) for r in reports) for key in keys},
    "individual":reports,
    "limitations":"Event counts are log-derived; world seeds do not guarantee deterministic timing."
}
dest=pathlib.Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(aggregate,indent=2)+"\n")
print(json.dumps({k:v for k,v in aggregate.items() if k!="individual"},indent=2))
