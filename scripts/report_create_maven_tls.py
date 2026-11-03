#!/usr/bin/env python3
"""Strict, non-bypassing CI TLS/preflight diagnostic for Create Maven.

No insecure TLS flags, untrusted certificate import, or dependency rewriting.
Network probes are in CI shell workflow. This script classifies their records.
"""
import argparse
import json
from pathlib import Path

EXPECTED=("create_pom","flywheel_pom","ponder_pom","registrate_pom")

def classify(data):
    if not isinstance(data,dict) or set(data)!=set(EXPECTED):
        raise ValueError("Missing exact dependency endpoints")
    out={}
    for key in EXPECTED:
        row=data[key]
        if not isinstance(row,dict) or set(row)!={"http_code","curl_exit","ca_verified","url"}:
            raise ValueError("Malformed endpoint record")
        if type(row["curl_exit"]) is not int or type(row["ca_verified"]) is not bool:
            raise ValueError("Missing TLS validation")
        if type(row["http_code"]) is not int or not 0 <= row["http_code"] <= 599:
            raise ValueError("Invalid HTTP code")
        if type(row["url"]) is not str or not row["url"].startswith("https://"):
            raise ValueError("Insecure or invalid Maven origin")
        if not row["ca_verified"] or row["curl_exit"]!=0:
            status="TLS_OR_TRANSPORT_FAILURE"
        elif row["http_code"]==200:
            status="HTTPS_REACHABLE"
        else:
            status="HTTP_ERROR"
        out[key]={"status":status,"http_code":row["http_code"],
                  "ca_verified":row["ca_verified"],"origin":row["url"].split("/")[2]}
    return {"schema":"hearthbound.create-maven-tls-diagnostics.v1",
            "tls_verification_disabled":False,
            "dependencies_modified":False,
            "endpoints":out,
            "all_endpoints_reachable":all(x["status"]=="HTTPS_REACHABLE" for x in out.values())}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("raw",type=Path)
    p.add_argument("--output",type=Path,default=Path("create-maven-diagnostic.json"))
    args=p.parse_args()
    result=classify(json.loads(args.raw.read_text()))
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("CREATE_MAVEN_TLS_DIAGNOSTICS",json.dumps(result,sort_keys=True))
    if not result["all_endpoints_reachable"]:
        raise SystemExit("At least one official dependency URL failed validated HTTPS; no insecure bypass attempted")
if __name__=="__main__":
    main()
