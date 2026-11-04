#!/usr/bin/env python3
"""Opt-in real-Forge neural attention canary after standard RCON regression.

Runs only in disposable research CI. Neural selects one registered source per
existing budget interval; no movement, task, inventory mutation or hidden data.
"""
import json
import os
import re
import socket
import struct
import time
from pathlib import Path
from validate_forge_attention_pair import pair

def packet(number,kind,content):
    payload=struct.pack("<ii",number,kind)+content.encode()+b"\0\0"
    return struct.pack("<i",len(payload))+payload

def exact(sock,count):
    output=b""
    while len(output)<count:
        data=sock.recv(count-len(output))
        if not data:raise ConnectionError("RCON socket disconnected")
        output+=data
    return output

def frame(sock,id,allow_empty=False):
    for _ in range(40):
        length=struct.unpack("<i",exact(sock,4))[0]
        if length<10 or length>1000000:raise ValueError("Invalid RCON frame")
        data=exact(sock,length)
        number,kind=struct.unpack("<ii",data[:8])
        result=data[8:-2].decode(errors="replace")
        if number!=id:raise ValueError("RCON request identity mismatch")
        if allow_empty:
            # Minecraft may send an empty type-0 packet before auth type 2.
            if kind==2:return result
            continue
        if result.strip():return result
    raise ValueError("No command response")

def main():
    with socket.create_connection(("127.0.0.1",25575),timeout=15) as sock:
        sock.settimeout(20)
        sock.sendall(packet(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
        frame(sock,1,allow_empty=True)
        next_id=10
        def run(command):
            nonlocal next_id
            sock.sendall(packet(next_id,2,command))
            result=frame(sock,next_id)
            next_id+=1
            return result
        disabled=run("hearthbound citizen_neural_status")
        if "status=DISABLED" not in disabled:
            raise AssertionError("Neural selector must default to disabled: "+disabled)
        enabled=run("hearthbound citizen_neural_enable")
        if "status=ACTIVE" not in enabled or "sha256=" not in enabled:
            raise AssertionError("Could not enable frozen model: "+enabled)
        started=run("hearthbound citizen_log_start")
        if "status=STARTED" not in started:
            raise AssertionError("Could not start separate neural canary journal: "+started)
        citizen="@e[type=minecraft:villager,name=Sable,limit=1]"
        moved=run("tp "+citizen+" 9 100 3")
        if "teleported" not in moved.lower():
            raise AssertionError("Sable canary citizen unavailable: "+moved)
        for pos in ("9 100 2","10 100 2"):
            registered=run("hearthbound citizen_watch "+pos+" "+citizen)
            if "status=REGISTERED" not in registered:
                raise AssertionError("Neural canary watch failed: "+registered)
        found=None
        for _ in range(90):
            choice=run("hearthbound citizen_opportunity_latest")
            outcome=run("hearthbound citizen_outcome_latest")
            if "policy=NEURAL_CAUSAL_MLP_OPT_IN" not in choice:
                time.sleep(.15)
                continue
            try:
                event=pair(choice,outcome)
                if len(event["opportunity"]["candidates"])==2:
                    found=event
                    break
            except ValueError:
                pass
            time.sleep(.15)
        if found is None:raise AssertionError("No real neural-selected Forge observation")
        if found["opportunity"]["policy"]!="NEURAL_CAUSAL_MLP_OPT_IN":
            raise AssertionError("Actual verified policy attribution is not neural")
        if found["opportunity"]["inventory_read"] is not False:
            raise AssertionError("Neural policy had pre-inspection inventory access")
        if found["opportunity"]["action_authorized"] is not False:
            raise AssertionError("Neural selector gained task authority")
        if found["opportunity"]["budget"]!=1:
            raise AssertionError("Neural selector exceeded source budget")
        if found["opportunity"]["selected"] not in found["opportunity"]["candidates"]:
            raise AssertionError("Neural choice not in registered candidates")
        if found["outcome"]["status"]!="OBSERVED":
            raise AssertionError("Neural choice did not produce a valid direct inspection")
        for pos in ("9 100 2","10 100 2"):
            result=run("hearthbound citizen_unwatch "+pos+" "+citizen)
            if "removed=true" not in result:
                raise AssertionError("Canary cleanup failed: "+result)
        stopped=run("hearthbound citizen_log_stop")
        if "manifest=FINALIZED" not in stopped:
            raise AssertionError("Failed to seal real neural canary evidence: "+stopped)
        # This canary starts a fresh durable journal separately from the
        # baseline, so any existing journal from prior server runs is distinct.
        disabled_again=run("hearthbound citizen_neural_disable")
        if "status=DISABLED" not in disabled_again:
            raise AssertionError("Cannot turn off neural control")
    result={"schema":"hearthbound.live-neural-attention-canary.v1",
            "origin":"REAL_FORGE_RCON",
            "policy":"NEURAL_CAUSAL_MLP_OPT_IN",
            "model_sha256":enabled.split("sha256=")[1].split()[0],
            "selected":found["opportunity"]["selected"],
            "candidate_count":len(found["opportunity"]["candidates"]),
            "selected_observation_status":found["outcome"]["status"],
            "observed_selected_source_only":True,
            "neural_training_origin":"SIMULATED_CAUSAL_HISTORY_ONLY",
            "navigation_actions_authorized":False,
            "inventory_mutations_authorized":False,
            "counterfactual_rewards_inferred":False}
    Path("real-neural-attention-canary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("LIVE_FORGE_NEURAL_ATTENTION_CANARY_PASS selected="+result["selected"]+
          " model="+result["model_sha256"]+" budget=1 actions=false")

if __name__=="__main__":
    main()
