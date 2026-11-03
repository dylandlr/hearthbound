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
    # Second citizen independently observes a different real chest, not
    # a shared global source cache or an incoming hearsay message.
    run("setblock 9 100 2 minecraft:chest replace")
    stocked=run('data merge block 9 100 2 {Items:[{Slot:0b,id:"minecraft:wheat",Count:3b}]}')
    if "modified" not in stocked.lower():
        raise AssertionError("Could not construct second physical source: "+stocked)
    sable="@e[type=minecraft:villager,name=Sable,limit=1]"
    sable_before=run("hearthbound citizen_memory 9 100 2 "+sable)
    receiver_before=run("hearthbound citizen_memory 9 100 2 "+recipient)
    if "status=UNKNOWN" not in sable_before or "status=UNKNOWN" not in receiver_before:
        raise AssertionError("Second source was known before direct citizen observation")
    observation=run("hearthbound citizen_observe 9 100 2 "+recipient)
    if "status=OBSERVED" not in observation or "wheat=3" not in observation or "action_authorized=false" not in observation:
        raise AssertionError("Recipient did not independently observe real chest: "+observation)
    receiver_after=run("hearthbound citizen_memory 9 100 2 "+recipient)
    sable_after=run("hearthbound citizen_memory 9 100 2 "+sable)
    if "status=KNOWN" not in receiver_after or "wheat=3" not in receiver_after or "origin=DIRECT_FORGE_OBSERVATION" not in receiver_after:
        raise AssertionError("Independent recipient memory not retained: "+receiver_after)
    if "status=UNKNOWN" not in sable_after:
        raise AssertionError("Sable learned recipient private observation without communication: "+sable_after)
    hearsay_only=run("hearthbound citizen_memory 6 100 2 "+recipient)
    if "status=UNKNOWN" not in hearsay_only:
        raise AssertionError("Incoming report improperly promoted to direct memory: "+hearsay_only)
    run("hearthbound perception_unwatch 6 100 2")
    print("REAL_FORGE_SOCIAL_REPORT_ACCEPTANCE_PASS",flush=True)
