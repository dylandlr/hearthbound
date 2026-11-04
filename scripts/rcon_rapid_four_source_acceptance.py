#!/usr/bin/env python3
"""Execute 16 fast resource changes on four real Forge chests via RCON.

Separate post-restart operator canary: leaves the historical two-source
experiment untouched. The neural controller only selects registered watches.
"""
import json
import os
import re
import socket
import struct
import time
from pathlib import Path
from rapid_four_source_schedule import SOURCES,INITIAL,plan,rcon_command,verify

def send(sock,number,kind,content):
    body=struct.pack("<ii",number,kind)+content.encode()+b"\0\0"
    sock.sendall(struct.pack("<i",len(body))+body)

def exact(sock,n):
    out=b""
    while len(out)<n:
        part=sock.recv(n-len(out))
        if not part:raise ConnectionError("RCON closed")
        out+=part
    return out

def response(sock,id,auth=False):
    for _ in range(30):
        length=struct.unpack("<i",exact(sock,4))[0]
        if not 10<=length<=1000000:raise ValueError("invalid RCON frame")
        body=exact(sock,length)
        rid,kind=struct.unpack("<ii",body[:8])
        if rid!=id:raise ValueError("RCON ID mismatch")
        text=body[8:-2].decode(errors="replace")
        if auth:
            if kind==2:return text
        elif text.strip():
            return text
    raise ValueError("RCON missing reply")

def tick(run):
    value=run("time query gametime")
    terms=re.findall(r"\d+",value)
    if not terms:raise AssertionError("Minecraft did not return game tick: "+value)
    return int(terms[-1])

def main():
    seed=os.environ["HEARTHBOUND_WORLD_SEED"]
    mode=os.environ.get("HEARTHBOUND_ATTENTION_MODE","scripted")
    if mode not in ("scripted","neural"):
        raise ValueError("Invalid attention arm")
    scheduled=plan(seed)
    with socket.create_connection(("127.0.0.1",25575),timeout=15) as sock:
        sock.settimeout(20)
        send(sock,1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"])
        response(sock,1,auth=True)
        counter=11
        def run(command):
            nonlocal counter
            send(sock,counter,2,command)
            result=response(sock,counter)
            counter+=1
            return result
        initial=run("hearthbound citizen_neural_status")
        if "status=DISABLED" not in initial:
            raise AssertionError("Challenge must begin with scripted default")
        citizen="@e[type=minecraft:villager,name=Sable,limit=1]"
        if "teleported" not in run("tp "+citizen+" 8 100 3").lower():
            raise AssertionError("Citizen absent from real Forge")
        for source,wheat in zip(SOURCES,INITIAL):
            result=run("setblock "+source+" minecraft:chest replace")
            if "changed" not in result.lower():
                raise AssertionError("Could not place real chest: "+result)
            result=run(rcon_command(source,wheat))
            if "modified" not in result.lower():
                raise AssertionError("Could not stock challenge chest: "+result)
        started=run("hearthbound citizen_log_start")
        if "status=STARTED" not in started:
            raise AssertionError("Challenge attention journal not started")
        for source in SOURCES:
            result=run("hearthbound citizen_watch "+source+" "+citizen)
            if "status=REGISTERED" not in result:
                raise AssertionError("Cannot register all four watched sources: "+result)
        enabled=None
        if mode=="neural":
            enabled=run("hearthbound citizen_neural_enable")
            if "status=ACTIVE" not in enabled:
                raise AssertionError("Neural selector did not activate: "+enabled)
        executions=[]
        for step in scheduled["steps"]:
            before=tick(run)
            reply=run(rcon_command(step["source"],step["wheat"]))
            if "modified" not in reply.lower():
                raise AssertionError("Real Forge inventory change not confirmed: "+reply)
            after=tick(run)
            executions.append({"index":step["index"],"source":step["source"],
                               "wheat":step["wheat"],"tick_before":before,
                               "tick_after":after,"status":"RCON_MODIFIED"})
            time.sleep(step["pause_seconds"])
        # The final measurement window exists before restoring any fixture.
        time.sleep(.6)
        stop_tick=tick(run)
        if mode=="neural":
            disabled=run("hearthbound citizen_neural_disable")
            if "status=DISABLED" not in disabled:
                raise AssertionError("Neural selector did not shut down")
        for source in SOURCES:
            result=run("hearthbound citizen_unwatch "+source+" "+citizen)
            if "removed=true" not in result:
                raise AssertionError("Could not clean up four-source watch: "+result)
        finished=run("hearthbound citizen_log_stop")
        if "status=STOPPED" not in finished:
            raise AssertionError("Could not finalize four-source journal: "+finished)
    executed={"schema":"hearthbound.rapid-four-resource-execution.v1",
              "origin":"REAL_FORGE_RCON",
              "configured_world_seed":seed,
              "plan_sha256":scheduled["sha256"],
              "policy":("NEURAL_CAUSAL_MLP_OPT_IN" if mode=="neural" else "LEAST_RECENTLY_SAMPLED"),
              "model_sha256":None if enabled is None else enabled.split("sha256=")[1].split()[0],
              "executions":executions,
              "measurement_stop_tick":stop_tick,
              "counterfactual_outcomes_inferred":False}
    verified=verify(executed)
    Path("rapid-four-execution.json").write_text(json.dumps(executed,indent=2,sort_keys=True)+"\n")
    Path("rapid-four-verified.json").write_text(json.dumps(verified,indent=2,sort_keys=True)+"\n")
    print("REAL_FORGE_RAPID_FOUR_EXECUTION_PASS policy="+executed["policy"]+
          " interventions="+str(verified["verified_interventions"]))

if __name__=="__main__":
    main()
