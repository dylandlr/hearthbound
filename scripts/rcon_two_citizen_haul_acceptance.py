#!/usr/bin/env python3
"""Acceptance: two actual Forge villagers contend for a source, then haul in parallel.

Disposable CI world only. Interventions are operator-owned and never attributed
to learned citizen policy. Explicitly require physical inventory changes and
release of both durable source claims. No automatic claim repair.
"""
import os
import socket
import struct
import time

from haul_smoke_diagnostics import POLL_COUNT,POLL_INTERVAL_SECONDS

PASS="test passed"

def packet(request_id,kind,content):
    data=struct.pack("<ii",request_id,kind)+content.encode()+b"\0\0"
    return struct.pack("<i",len(data))+data

def exact(sock,n):
    data=b""
    while len(data)<n:
        chunk=sock.recv(n-len(data))
        if not chunk:raise ConnectionError("RCON connection closed")
        data+=chunk
    return data

def response(sock,request_id):
    for _ in range(16):
        length=struct.unpack("<i",exact(sock,4))[0]
        if not 10<=length<=1000000:raise ValueError("invalid RCON length")
        frame=exact(sock,length)
        rid,kind=struct.unpack("<ii",frame[:8])
        if rid!=request_id:
            raise AssertionError("RCON response mismatch "+str((request_id,rid)))
        message=frame[8:-2].decode(errors="replace")
        if message.strip():return message
    raise AssertionError("No nonempty RCON response for "+str(request_id))

class Rcon:
    def __init__(self,sock):
        self.sock=sock
        self.next_id=20
    def run(self,command):
        rid=self.next_id
        self.next_id+=1
        self.sock.sendall(packet(rid,2,command))
        actual=response(self.sock,rid)
        print("MULTI_CITIZEN_RCON id="+str(rid)+" command="+repr(command)+
              " response="+repr(actual),flush=True)
        return actual
    def require(self,command,expected):
        answer=self.run(command)
        if expected.lower() not in answer.lower():
            raise AssertionError(f"Expected {expected!r}: {command}: {answer}")
        return answer

CITIZEN_A="execute positioned 4 100 1 run "
CITIZEN_B="execute positioned 22 100 1 run "
CHECK_DEST_A='execute if data block 7 100 1 Items[{id:"minecraft:wheat",Count:1b}]'
CHECK_DEST_B='execute if data block 19 100 1 Items[{id:"minecraft:wheat",Count:1b}]'

def require_counts(rcon,from_a,to_a,from_b,to_b):
    # RCON 'data get block ... Items' values preserve actual Minecraft state.
    # Exact quantities are additionally verified with native execute-if-data.
    for point,count in ((11,from_a),(7,to_a),(24,from_b),(19,to_b)):
        rcon.require(
            f'execute if data block {point} 100 1 Items[{{id:"minecraft:wheat",Count:{count}b}}]',
            PASS)

def run_trial(rcon,sleep=time.sleep):
    rcon.require("forceload add 0 0 31 4","force loaded")
    rcon.require("fill 0 99 0 31 99 4 minecraft:stone","filled")
    rcon.require("fill 0 100 0 31 103 4 minecraft:air","filled")
    for point in (7,11,19,24):
        rcon.require(f"setblock {point} 100 1 minecraft:chest replace","changed the block")
    for point in (11,24):
        rcon.require(
            f'data merge block {point} 100 1 {{Items:[{{Slot:0b,id:"minecraft:wheat",Count:8b}}]}}',
            "modified")
    rcon.require(CITIZEN_A+"sable spawn","Sable spawned")
    rcon.require(CITIZEN_B+"sable spawn","Sable spawned")
    rcon.require("execute if entity @e[type=minecraft:villager,name=Sable]","test passed")
    # Assignment from distinct operator positions selects the nearest marked
    # citizen; both citizens' assignments use the exact same shared chest.
    rcon.require(CITIZEN_A+"sable haul 11 100 1 7 100 1","Sable assigned wheat haul")
    count=rcon.require("hearthboundclaims count","Active source claims")
    if "Active source claims in this dimension: 1" not in count:
        raise AssertionError("first source was not exclusively reserved")
    conflict=rcon.run(CITIZEN_B+"sable haul 11 100 1 19 100 1")
    if "source already claimed by another citizen" not in conflict.lower():
        raise AssertionError("Second citizen did not receive source-claim rejection: "+conflict)
    rcon.require("hearthboundclaims owner 11 100 1","Claim at")
    # A losing citizen can independently reserve a DIFFERENT physical source.
    rcon.require(CITIZEN_B+"sable haul 24 100 1 19 100 1","Sable assigned wheat haul")
    count=rcon.require("hearthboundclaims count","Active source claims")
    if "Active source claims in this dimension: 2" not in count:
        raise AssertionError("two independent real Minecraft claims not active: "+count)
    audit_a=rcon.require(CITIZEN_A+"sable haul-audit","AUDIT job=")
    audit_b=rcon.require(CITIZEN_B+"sable haul-audit","AUDIT job=")
    for label,audit in (("A",audit_a),("B",audit_b)):
        if "claim=owned" not in audit:
            raise AssertionError(label+" did not own a claim: "+audit)
    if "source=BlockPos{x=11" not in audit_a or "source=BlockPos{x=24" not in audit_b:
        raise AssertionError("wrong citizen selected for either job")

    delivered_a=delivered_b=False
    for tick in range(POLL_COUNT):
        sleep(POLL_INTERVAL_SECONDS)
        if not delivered_a:
            delivered_a=PASS in rcon.run(CHECK_DEST_A).lower()
        if not delivered_b:
            delivered_b=PASS in rcon.run(CHECK_DEST_B).lower()
        if delivered_a and delivered_b:
            print("MULTI_CITIZEN_PHYSICAL_DELIVERY poll="+str(tick+1)+
                  " both_delivered=true",flush=True)
            break
        if tick in (14,29,44,59):
            for label,location in (("A",CITIZEN_A),("B",CITIZEN_B)):
                print("MULTI_CITIZEN_CHECKPOINT label="+label+" poll="+str(tick+1)
                      +" audit="+rcon.run(location+"sable haul-audit"),flush=True)
    if not (delivered_a and delivered_b):
        raise AssertionError("Two real villagers did not independently deliver before 150s: "+
                             str((delivered_a,delivered_b)))
    require_counts(rcon,7,1,7,1)
    rcon.require("hearthboundclaims count","Active source claims in this dimension: 0")
    rcon.require("hearthboundclaims owner 11 100 1","No source claim")
    rcon.require("hearthboundclaims owner 24 100 1","No source claim")
    # A completion message is insufficient; check both exact final chest
    # inventories, plus each citizen's proximity to its OWN destination.
    rcon.require(
        "execute positioned 7.5 100 1.5 if entity @e[type=minecraft:villager,name=Sable,distance=..2.6]",
        PASS)
    rcon.require(
        "execute positioned 19.5 100 1.5 if entity @e[type=minecraft:villager,name=Sable,distance=..2.6]",
        PASS)
    print("MULTI_CITIZEN_FORGE_ACCEPTANCE_PASS source_conflict_rejected=true "
          "distinct_source_claims=2 physical_deliveries=2 "
          "source_count_each=7 destination_count_each=1 "
          "no_outstanding_claims=true",flush=True)

def main():
    with socket.create_connection(("127.0.0.1",25575),timeout=15) as sock:
        sock.settimeout(20)
        sock.sendall(packet(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
        for _ in range(4):
            n=struct.unpack("<i",exact(sock,4))[0]
            if not 10<=n<=1000000:raise ValueError("invalid RCON auth frame")
            body=exact(sock,n)
            request_id,_=struct.unpack("<ii",body[:8])
            if request_id==1:break
        else:raise AssertionError("RCON authentication failed")
        run_trial(Rcon(sock))
if __name__=="__main__":
    main()
