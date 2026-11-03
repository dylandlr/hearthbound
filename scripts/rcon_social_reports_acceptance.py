#!/usr/bin/env python3
"""Real Forge social report acceptance, following successful perception acceptance.

This fixture summons a second marked citizen and proves that knowledge delivery
requires explicit local communication, is recipient-owned, and never authorizes
Minecraft work. Uses actual source observation already collected by the server.
"""
import os
import socket
import struct
import time

def pkt(request_id, kind, value):
    body=struct.pack("<ii",request_id,kind)+value.encode()+b"\0\0"
    return struct.pack("<i",len(body))+body

def read_exact(sock,n):
    out=b""
    while len(out)<n:
        fragment=sock.recv(n-len(out))
        if not fragment: raise ConnectionError("RCON connection closed")
        out+=fragment
    return out

def get_response(sock,request_id):
    for _ in range(10):
        size=struct.unpack("<i",read_exact(sock,4))[0]
        if size<10 or size>1000000: raise ValueError("invalid RCON frame")
        frame=read_exact(sock,size)
        rid,kind=struct.unpack("<ii",frame[:8])
        if rid!=request_id: raise AssertionError("RCON request mismatch")
        result=frame[8:-2].decode(errors="replace")
        if result.strip(): return result
    raise AssertionError("missing RCON response")

with socket.create_connection(("127.0.0.1",25575),timeout=15) as sock:
    sock.settimeout(20)
    sock.sendall(pkt(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
    for _ in range(3):
        n=struct.unpack("<i",read_exact(sock,4))[0]
        frame=read_exact(sock,n)
        rid,_=struct.unpack("<ii",frame[:8])
        if rid==1:break
    else:raise AssertionError("RCON auth failed")
    counter=10
    def run(command):
        global counter
        sock.sendall(pkt(counter,2,command))
        result=get_response(sock,counter)
        counter+=1
        print(command,"=>",result,flush=True)
        return result

    # The v0.11.3 acceptance has stopped watching the source, leaving the
    # last direct evidence stale. A new explicit watch refreshes Sable's memory.
    run("hearthbound perception_watch 6 100 2")
    refreshed=False
    for _ in range(45):
        memory=run("hearthbound knowledge_source 6 100 2")
        if "status=KNOWN" in memory and "freshness=FRESH" in memory:
            refreshed=True
            break
        time.sleep(.2)
    if not refreshed: raise AssertionError("Sable did not obtain fresh direct evidence")

    # Unique marker makes entity selection independent of generated UUID.
    run('summon minecraft:villager 8 100 3 {CustomName:\'{"text":"HearthboundRecipient"}\',Tags:["hb_report_recipient"],ForgeData:{"hearthbound.citizen":1b}}')
    recipient="@e[type=minecraft:villager,tag=hb_report_recipient,limit=1]"
    before=run("hearthbound knowledge_report 6 100 2 "+recipient)
    if "status=UNKNOWN" not in before: raise AssertionError("Recipient had omniscient pre-share knowledge")
    sent=run("hearthbound knowledge_share 6 100 2 "+recipient)
    if "status=DELIVERED" not in sent or "action_authorized=false" not in sent:
        raise AssertionError("Explicit report not delivered: "+sent)
    report=run("hearthbound knowledge_report 6 100 2 "+recipient)
    if "status=REPORTED" not in report or "origin=REPORTED_DIRECT_FORGE_OBSERVATION" not in report or "action_authorized=false" not in report:
        raise AssertionError("Recipient report lost provenance: "+report)
    direct=run("hearthbound knowledge_source 6 100 2")
    if "origin=DIRECT_FORGE_OBSERVATION" not in direct:
        raise AssertionError("Sender's direct evidence overwritten by report")
    duplicate=run("hearthbound knowledge_share 6 100 2 "+recipient)
    if "status=DUPLICATE" not in duplicate:
        raise AssertionError("Duplicate report was not replay protected: "+duplicate)
    run("hearthbound perception_unwatch 6 100 2")
    print("REAL_FORGE_SOCIAL_REPORT_ACCEPTANCE_PASS",flush=True)
