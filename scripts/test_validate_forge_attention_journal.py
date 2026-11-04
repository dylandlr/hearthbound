#!/usr/bin/env python3
"""Tampering, order, provenance and attribution tests for durable Forge journal."""
import base64
import hashlib
import json
import validate_forge_attention_journal as j
from test_validate_forge_attention_pair import C,O

RUN="11111111-1111-4111-8111-111111111111"

def assemble(pairs):
    previous="GENESIS"
    rows=[]
    for n,(choice,outcome) in enumerate(pairs,1):
        payload=base64.urlsafe_b64encode((choice+"\n"+outcome).encode()).decode().rstrip("=")
        digest=hashlib.sha256((previous+"\n"+payload).encode()).hexdigest()
        rows.append(json.dumps(dict(schema=j.SCHEMA,run_id=RUN,sequence=n,
                                    previous_hash=previous,payload_b64=payload,sha256=digest)))
        previous=digest
    return "\n".join(rows)+"\n"

def denied(value):
    try:j.verify_text(value)
    except ValueError:return
    raise AssertionError("invalid journal accepted")

def main():
    first=(C,O)
    later=(C.replace("tick=100","tick=105"),
           O.replace("tick=100","tick=105"))
    valid=assemble([first,later])
    output=j.verify_text(valid,minimum=2)
    assert output["records"]==2 and output["observed"]==2
    assert output["hash_chain_valid"]
    assert output["minecraft_actions_authorized"] is False
    assert output==j.verify_text(valid,minimum=2)
    denied(valid.rstrip("\n"))
    denied(assemble([first]).replace('"sequence": 1','"sequence": 2'))
    denied(assemble([first,later]).replace('"previous_hash": "', '"previous_hash": "BAD'))
    denied(assemble([first,later]).replace('"run_id": "'+RUN,'"run_id": "00000000-0000-4000-8000-000000000000',1))
    denied(assemble([later,first]))
    denied(assemble([(C,O.replace("wheat=3","wheat=7"))]).replace("7","6",1))
    denied(assemble([(C,O.replace("observer=11111111","observer=22222222"))]))
    denied(assemble([(C,O.replace("action_authorized=false","action_authorized=true"))]))
    denied(assemble([(C+" wheat=4",O)]))
    print("ATTENTION_DURABLE_JOURNAL_CONTRACT_PASS")

if __name__=="__main__":
    main()
