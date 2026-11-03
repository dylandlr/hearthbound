#!/usr/bin/env python3
"""Exercise real read-only Forge perception receipts in a disposable RCON world.

Run AFTER scripts/rcon_smoke.py, BEFORE the server persistence checkpoint.
Fails if no actual server observation occurs. No fabricated receipt fixture,
client RGB capture, neural action, or on-server learning.
"""
import json
import os
import re
import socket
import struct
import time
from pathlib import Path
from validate_live_perception_receipts import parse, validate_lines

HOST="127.0.0.1"
PORT=25575
SOURCE="6,100,2"
PASSWORD=os.environ["HEARTHBOUND_RCON_PASSWORD"]
RECEIPTS=[]
REQUESTS=[]

def packet(request_id,kind,payload):
    body=struct.pack("<ii",request_id,kind)+payload.encode()+b"\x00\x00"
    return struct.pack("<i",len(body))+body

def exact(sock,count):
    result=b""
    while len(result)<count:
        data=sock.recv(count-len(result))
        if not data:raise ConnectionError("RCON disconnected")
        result+=data
    return result

def read(sock,request_id):
    for _ in range(30):
        size=struct.unpack("<i",exact(sock,4))[0]
        if size<10 or size>1000000:raise ValueError("Invalid RCON frame length")
        frame=exact(sock,size)
        rid,_=struct.unpack("<ii",frame[:8])
        content=frame[8:-2].decode(errors="replace")
        if rid!=request_id:
            raise AssertionError("RCON frame out of order")
        if content.strip():return content
    raise AssertionError("RCON response was empty")

def main():
    with socket.create_connection((HOST,PORT),timeout=15) as sock:
        sock.settimeout(20)
        sock.sendall(packet(1,3,PASSWORD))
        for _ in range(3):
            size=struct.unpack("<i",exact(sock,4))[0]
            frame=exact(sock,size)
            rid,_=struct.unpack("<ii",frame[:8])
            if rid==1:break
        else:raise AssertionError("RCON authentication failed")
        rid=10
        def command(value):
            nonlocal rid
            sock.sendall(packet(rid,2,value))
            outcome=read(sock,rid)
            rid+=1
            REQUESTS.append({"command":value,"response":outcome})
            return outcome

        # Source is separate from the mill / prior trial's source and does
        # not interrupt its verified policy/experience bookkeeping.
        resp=command("forceload add 0 0 10 4")
        if "could not" in resp.lower() or "unknown" in resp.lower():
            raise AssertionError("Could not load observation fixture: "+resp)
        resp=command("tp @e[type=minecraft:villager,name=Sable,limit=1] 6 100 3")
        if "teleported" not in resp.lower():
            raise AssertionError("Sable observer not available: "+resp)

        resp=command("setblock 6 100 2 minecraft:chest replace")
        if "changed" not in resp.lower():
            raise AssertionError("Failed to install empty source: "+resp)
        resp=command("hearthbound perception_watch 6 100 2")
        if "status=REGISTERED" not in resp or "mode=READ_ONLY" not in resp:
            raise AssertionError("Watch registration failed: "+resp)

        def receive(expected_state,expected_wheat,greater_revision=None):
            for _ in range(55):
                value=command("hearthbound perception_latest")
                found=parse(value)
                if found is not None and found["state"]==expected_state and found["wheat"]==expected_wheat:
                    if greater_revision is None or found["revision"]>greater_revision:
                        if found["source"]!=SOURCE or found["dimension"]!="minecraft:overworld":
                            raise AssertionError("Observed wrong source: "+value)
                        RECEIPTS.append(value)
                        return found
                time.sleep(0.2)
            raise AssertionError(f"Timed out awaiting live {expected_state}/{expected_wheat} receipt")

        empty=receive("EMPTY",0)
        resp=command('setblock 6 100 2 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:4b}]} replace')
        if "changed" not in resp.lower():
            raise AssertionError("Could not add wheat to source: "+resp)
        stocked=receive("AVAILABLE",4,empty["revision"])
        resp=command("setblock 6 100 2 minecraft:chest replace")
        if "changed" not in resp.lower():
            raise AssertionError("Could not empty source: "+resp)
        emptied=receive("EMPTY",0,stocked["revision"])
        assert [x["revision"] for x in (empty,stocked,emptied)]==[
            empty["revision"],empty["revision"]+1,empty["revision"]+2]
        if not empty["tick"]<=stocked["tick"]<=emptied["tick"]:
            raise AssertionError("Nonmonotonic server ticks")

        verified=validate_lines(RECEIPTS)
        if verified["receipts"]!=3 or verified["distinct_sources"]!=1:
            raise AssertionError("Incomplete live receipt chain")
        status=command("hearthbound perception_receipts")
        if "PERCEPTION_STATUS" not in status and "PERCEPTION_RECEIPT" not in status:
            raise AssertionError("Receipt history command missing")
        removed=command("hearthbound perception_unwatch 6 100 2")
        if "removed=true" not in removed:
            raise AssertionError("Source watch not removed")
        # Main thread sampling remains passive; independently collected RCON
        # state is only an acceptance fixture, NOT neural-model input.
        Path("real-perception-receipts.txt").write_text("\n".join(RECEIPTS)+"\n")
        report={
            "schema":"hearthbound.real-forge-perception-acceptance.v1",
            "origin":"REAL_FORGE_RCON",
            "minecraft_worlds":1,
            "verified_events":verified["receipts"],
            "source":SOURCE,
            "states":[{"revision":x["revision"],"tick":x["tick"],
                       "state":x["state"],"wheat":x["wheat"]} for x in
                      (empty,stocked,emptied)],
            "source_inventory_changes_tested":True,
            "source_action_authorized":False,
            "neural_learning_performed":False,
            "camera_frames_captured":0,
            "vision_models_trained":0,
        }
        Path("real-perception-acceptance.json").write_text(
            json.dumps(report,sort_keys=True,indent=2)+"\n")
        print("VERIFIED_REAL_FORGE_PERCEPTION "+json.dumps(report,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
