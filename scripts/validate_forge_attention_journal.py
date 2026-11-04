#!/usr/bin/env python3
"""Verify on-disk Forge citizen attention journal, including SHA-256 hash chain.

Each journal entry has a run_id, strictly increasing sequence and a base64url
pair of pre-choice and actual outcome strings. No unchosen source truth.
"""
import argparse
import base64
import hashlib
import json
import re
from pathlib import Path
from validate_forge_attention_pair import pair

SCHEMA="hearthbound.attention-journal.v1"
UUID=re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

def verify_text(contents,minimum=1):
    if not contents.endswith("\n"):
        raise ValueError("journal missing trailing record newline")
    lines=contents.splitlines()
    if len(lines)<minimum or not lines:
        raise ValueError("insufficient journal entries")
    previous="GENESIS"
    run_id=None
    prior_tick=-1
    observed=0
    unobserved=0
    selected_sources=set()
    for seq,line in enumerate(lines,1):
        try: row=json.loads(line)
        except json.JSONDecodeError as error: raise ValueError("invalid JSONL row") from error
        expected={"schema","run_id","sequence","previous_hash","payload_b64","sha256"}
        if not isinstance(row,dict) or set(row)!=expected:
            raise ValueError("invalid journal row fields")
        if row["schema"]!=SCHEMA or not isinstance(row["run_id"],str) or not UUID.fullmatch(row["run_id"]):
            raise ValueError("invalid journal identity")
        if run_id is None:run_id=row["run_id"]
        if row["run_id"]!=run_id or type(row["sequence"])!=int or row["sequence"]!=seq:
            raise ValueError("mixed run IDs or noncontiguous sequences")
        if row["previous_hash"]!=previous:
            raise ValueError("broken hash chain")
        encoded=row["payload_b64"]
        if not isinstance(encoded,str) or not re.fullmatch(r"[A-Za-z0-9_-]+",encoded):
            raise ValueError("invalid payload encoding")
        digest=hashlib.sha256((previous+"\n"+encoded).encode()).hexdigest()
        if row["sha256"]!=digest:raise ValueError("modified journal payload")
        try:
            payload=base64.urlsafe_b64decode(encoded+"="*((-len(encoded))%4)).decode("utf-8")
        except (ValueError,UnicodeError) as error:
            raise ValueError("invalid UTF-8 journal payload") from error
        parts=payload.split("\n")
        if len(parts)!=2:raise ValueError("not exactly one matched pair")
        result=pair(*parts)
        opportunity=result["opportunity"]
        outcome=result["outcome"]
        selected_sources.add((opportunity["observer"],opportunity["dimension"],opportunity["selected"]))
        if opportunity["tick"]<prior_tick:raise ValueError("journal tick regression")
        prior_tick=opportunity["tick"]
        if outcome["status"]=="OBSERVED":observed+=1
        else:unobserved+=1
        previous=digest
    return {"schema":"hearthbound.verified-attention-journal.v1",
            "origin":"REAL_FORGE_SERVER_FILE",
            "run_id":run_id,"records":len(lines),
            "observed":observed,"unobserved":unobserved,
            "distinct_observer_sources_selected":len(selected_sources),
            "final_hash":previous,"hash_chain_valid":True,
            "counterfactual_reward_available":False,
            "minecraft_actions_authorized":False,
            "note":"Append-only chain checks corruption and internal consistency, not authenticity against a hostile writer or undisclosed truncation"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input",type=Path)
    ap.add_argument("--min-records",type=int,default=1)
    ap.add_argument("--output",type=Path,default=Path("verified-attention-journal.json"))
    args=ap.parse_args()
    result=verify_text(args.input.read_text(),minimum=args.min_records)
    if args.input.name!="attention-"+result["run_id"]+".jsonl":
        raise ValueError("journal filename does not match its run ID")
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("FORGE_ATTENTION_JOURNAL_VERIFIED records="+str(result["records"])+
          " observed="+str(result["observed"])+
          " unobserved="+str(result["unobserved"])+
          " chain_valid=true execution=false")

if __name__=="__main__":
    main()
