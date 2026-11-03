#!/usr/bin/env python3
"""RCON persistence checkpoint for the same live Minecraft dedicated-server world."""
import os, socket, struct, sys

HOST, PORT = "127.0.0.1", 25575
PASSWORD = os.environ["HEARTHBOUND_RCON_PASSWORD"]
def packet(i, kind, data):
    body = struct.pack("<ii", i, kind) + data.encode() + b"\0\0"
    return struct.pack("<i", len(body)) + body
def exactly(sock, size):
    out = b""
    while len(out) < size:
        chunk = sock.recv(size-len(out))
        if not chunk: raise ConnectionError("RCON disconnected")
        out += chunk
    return out
def reply(sock):
    size = struct.unpack("<i", exactly(sock,4))[0]
    if size < 10 or size > 100000: raise ValueError("invalid RCON length")
    content = exactly(sock,size)
    return struct.unpack("<ii",content[:8])[0],content[8:-2].decode(errors="replace")
def run(sock,i,command):
    sock.sendall(packet(i,2,command))
    num,output = reply(sock)
    if num != i: raise RuntimeError("RCON id mismatch")
    print(command,output,flush=True)
    return output

mode=sys.argv[1]
with socket.create_connection((HOST,PORT),timeout=15) as sock:
    sock.settimeout(20)
    sock.sendall(packet(1,3,PASSWORD))
    rid,_=reply(sock)
    if rid!=1:rid,_=reply(sock)
    if rid!=1:raise RuntimeError("RCON authentication failed")
    if mode=="checkpoint":
        output=run(sock,2,'data get entity @e[type=minecraft:villager,name=Sable,limit=1] ForgeData."hearthbound.verifiedMillExperience.v1".observedVerifiedProcesses')
        if "1L" not in output: raise AssertionError("Sable's verified mill experience absent before save")
        memory=run(sock,5,"hearthbound knowledge_source 6 100 2")
        if "status=KNOWN" not in memory or "state=EMPTY" not in memory or "wheat=0" not in memory:
            raise AssertionError("Sable's live knowledge missing before save")
        # Independently observed citizen B source, not shared with Sable.
        recipient='@e[type=minecraft:villager,tag=hb_report_recipient,limit=1]'
        other=run(sock,6,"hearthbound citizen_memory 9 100 2 "+recipient)
        if "status=KNOWN" not in other or "wheat=3" not in other:
            raise AssertionError("Recipient direct-source knowledge missing before restart")
        output=run(sock,3,"save-all flush")
        if "Saved the game" not in output and "Saving" not in output: raise AssertionError("save-all flush did not confirm save")
        run(sock,4,"stop")
    elif mode=="verify":
        run(sock,2,"forceload add 0 0 10 4")
        output=run(sock,3,'execute if entity @e[type=minecraft:villager,name=Sable]')
        if "Test passed" not in output:raise AssertionError("Sable missing after restart")
        output=run(sock,4,'data get entity @e[type=minecraft:villager,name=Sable,limit=1] ForgeData."hearthbound.verifiedMillExperience.v1".observedVerifiedProcesses')
        if "1L" not in output:raise AssertionError("Sable's verified experience did not persist")
        memory=run(sock,5,"hearthbound knowledge_source 6 100 2")
        if "status=KNOWN" not in memory or "state=EMPTY" not in memory or "wheat=0" not in memory:
            raise AssertionError("Sable's source knowledge did not survive restart")
        if "action_authorized=false" not in memory:
            raise AssertionError("Remembering source unexpectedly authorized an action")
        recipient='@e[type=minecraft:villager,tag=hb_report_recipient,limit=1]'
        other=run(sock,6,"hearthbound citizen_memory 9 100 2 "+recipient)
        if "status=KNOWN" not in other or "wheat=3" not in other:
            raise AssertionError("Second citizen lost its own direct knowledge on server restart")
        sable=run(sock,7,'hearthbound citizen_memory 9 100 2 @e[type=minecraft:villager,name=Sable,limit=1]')
        if "status=UNKNOWN" not in sable:
            raise AssertionError("Second citizen source leaked into Sable memory after restart")
        print("MULTI_CITIZEN_DIRECT_KNOWLEDGE_SURVIVED_RESTART",flush=True)
        print("SABLE_SOURCE_KNOWLEDGE_SURVIVED_REAL_SERVER_RESTART",flush=True)
        print("SABLE_VERIFIED_EXPERIENCE_SURVIVED_REAL_SERVER_RESTART",flush=True)
    else:raise ValueError("expected checkpoint or verify")
