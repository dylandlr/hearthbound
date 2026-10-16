#!/usr/bin/env python3
"""Read-only verification that candidate evidence survived a real Forge restart."""
import os
import socket
import struct
import uuid

with open("mill-evidence-job.txt",encoding="utf-8") as file:
    job = str(uuid.UUID(file.read().strip()))

def packet(seq,typ,s):
    body=struct.pack("<ii",seq,typ)+s.encode()+b"\0\0"
    return struct.pack("<i",len(body))+body

def receive(sock):
    def exact(n):
        b=b""
        while len(b)<n:
            part=sock.recv(n-len(b))
            if not part: raise ConnectionError("RCON disconnected")
            b+=part
        return b
    size=struct.unpack("<i",exact(4))[0]
    data=exact(size)
    return struct.unpack("<i",data[:4])[0],data[8:-2].decode(errors="replace")

with socket.create_connection(("127.0.0.1",25575),timeout=20) as s:
    s.settimeout(20)
    s.sendall(packet(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
    response,_=receive(s)
    if response!=1: response,_=receive(s)
    assert response==1, "RCON authorization failed"
    s.sendall(packet(2,2,"sable mill-evidence "+job))
    response,output=receive(s)
    print("RESTART JOURNAL:",output,flush=True)
    assert response==2
    assert "MILL_EVIDENCE CANDIDATE job="+job in output
    assert "processingTick=" in output and "outputTick=" in output
    assert "NO_RESEARCH_CREDIT" in output
    s.sendall(packet(3,2,"sable mill-process "+job))
    response,receipt=receive(s)
    print("RESTART PROCESS RECEIPT:",receipt,flush=True)
    assert response==3
    assert "MILL_PROCESS VERIFIED_CALLBACK job="+job in receipt
    assert "wheatBefore=1 wheatAfter=0" in receipt
    assert "NO_RESEARCH_CREDIT" in receipt
    s.sendall(packet(4,2,"sable mill-reservation 7 101 1"))
    response,reservation=receive(s)
    print("RESTART MILL RESERVATION:",reservation,flush=True)
    assert response==4
    assert "MILL_RESERVATION HELD" in reservation and "job="+job in reservation
    print("PASS: Minecraft SavedData milling candidate and direct processing receipt survived server restart",flush=True)
