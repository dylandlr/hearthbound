#!/usr/bin/env python3
"""Verify complete Forge journal against explicit clean-stop manifest."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from validate_forge_attention_journal import verify_text

SCHEMA="hearthbound.attention-run-manifest.v1"

def verify(journal:Path, manifest:Path, minimum=1):
    if journal.is_symlink() or manifest.is_symlink():
        raise ValueError("symlinked journal or manifest not accepted")
    raw=journal.read_bytes()
    data=verify_text(raw.decode("utf-8"),minimum=minimum)
    try: meta=json.loads(manifest.read_text())
    except (ValueError,UnicodeError) as error:
        raise ValueError("invalid run manifest") from error
    if not isinstance(meta,dict) or set(meta)!={
        "schema","run_id","journal_file","records","final_hash",
        "journal_sha256","finalized","action_authorized"}:
        raise ValueError("invalid manifest contract")
    if meta["schema"]!=SCHEMA or meta["finalized"] is not True or meta["action_authorized"] is not False:
        raise ValueError("run not finalized or manifest grants authority")
    if meta["run_id"]!=data["run_id"] or meta["records"]!=data["records"] or type(meta["records"])!=int:
        raise ValueError("manifest count or identity mismatch")
    if meta["final_hash"]!=data["final_hash"]:
        raise ValueError("manifest chain tip mismatch")
    if meta["journal_file"]!=journal.name or journal.name!="attention-"+data["run_id"]+".jsonl":
        raise ValueError("manifest references wrong journal")
    if manifest.name!="attention-"+data["run_id"]+".manifest.json":
        raise ValueError("incorrect manifest filename")
    if meta["journal_sha256"]!=hashlib.sha256(raw).hexdigest():
        raise ValueError("journal file digest mismatch")
    return {"schema":"hearthbound.verified-attention-run.v1",
            "origin":"REAL_FORGE_SERVER_FILE",
            "run_id":data["run_id"],"records":data["records"],
            "final_hash":data["final_hash"],
            "journal_sha256":meta["journal_sha256"],
            "finalized":True,"integrity_verified":True,
            "minecraft_actions_authorized":False,
            "limits":"Detects alteration/truncation relative to the preserved manifest; not a signature or proof against tampering with both files"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("journal",type=Path)
    ap.add_argument("manifest",type=Path)
    ap.add_argument("--min-records",type=int,default=1)
    ap.add_argument("--output",type=Path,default=Path("verified-attention-run.json"))
    args=ap.parse_args()
    result=verify(args.journal,args.manifest,args.min_records)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("FINALIZED_REAL_FORGE_ATTENTION_RUN_VERIFIED records="+str(result["records"])
          +" integrity=true actions=false")

if __name__=="__main__":
    main()
