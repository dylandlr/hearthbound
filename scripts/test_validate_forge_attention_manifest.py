#!/usr/bin/env python3
"""Finalization regressions: missing manifest, truncation, altered seal and wrong run."""
import hashlib
import json
import tempfile
from pathlib import Path
from test_validate_forge_attention_journal import RUN,C,O,assemble
from validate_forge_attention_manifest import verify

def denied(journal,manifest):
    try: verify(journal,manifest)
    except ValueError:return
    raise AssertionError("unsealed or corrupted run accepted")

def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        journal=root/("attention-"+RUN+".jsonl")
        manifest=root/("attention-"+RUN+".manifest.json")
        valid=assemble([(C,O),(C.replace("tick=100","tick=105"),
                             O.replace("tick=100","tick=105"))])
        journal.write_text(valid)
        tip=json.loads(valid.splitlines()[-1])["sha256"]
        meta={"schema":"hearthbound.attention-run-manifest.v1",
              "run_id":RUN,"journal_file":journal.name,"records":2,
              "final_hash":tip,
              "journal_sha256":hashlib.sha256(journal.read_bytes()).hexdigest(),
              "finalized":True,"action_authorized":False}
        denied(journal,manifest) if manifest.exists() else None
        manifest.write_text(json.dumps(meta)+"\n")
        result=verify(journal,manifest,minimum=2)
        assert result["integrity_verified"] and result["records"]==2
        for key,value in (("records",1),("final_hash","0"*64),
                          ("journal_sha256","0"*64),("finalized",False),
                          ("action_authorized",True),("run_id","00000000-0000-4000-8000-000000000000")):
            fake=dict(meta)
            fake[key]=value
            manifest.write_text(json.dumps(fake)+"\n")
            denied(journal,manifest)
        manifest.write_text(json.dumps(meta)+"\n")
        journal.write_text(valid.splitlines()[0]+"\n")
        denied(journal,manifest)
        journal.write_text(valid)
        denied(journal,manifest.with_name("missing.json"))
    print("FINALIZED_ATTENTION_RUN_CONTRACT_PASS")

if __name__=="__main__":
    main()
