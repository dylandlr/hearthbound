#!/usr/bin/env python3
"""Real Create 6.0.8 milling experiment, on a disposable Forge CI world.

Power fixture: creative motor immediately below a millstone. Input: 1
wheat item dropped above the millstone. Requires observed output flour.
No agent knowledge or research reward is awarded by this test.
"""
import os
import socket
import struct
import time

def packet(req, typ, value):
    payload = struct.pack("<ii", req, typ) + value.encode() + b"\0\0"
    return struct.pack("<i", len(payload)) + payload

class Rcon:
    def __enter__(self):
        self.sock=socket.create_connection(("127.0.0.1",25575),timeout=20)
        self.sock.settimeout(20)
        self.seq=100
        self.sock.sendall(packet(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
        rid,_=self.receive()
        if rid!=1:
            rid,_=self.receive()
        if rid!=1: raise RuntimeError("RCON login failed")
        return self
    def __exit__(self,*_): self.sock.close()
    def receive(self):
        def exactly(n):
            out=b""
            while len(out)<n:
                part=self.sock.recv(n-len(out))
                if not part: raise ConnectionError("RCON socket closed")
                out+=part
            return out
        n=struct.unpack("<i",exactly(4))[0]
        if not 10<=n<=1000000: raise ValueError("Invalid packet length")
        raw=exactly(n)
        return struct.unpack("<i",raw[:4])[0],raw[8:-2].decode(errors="replace")
    def run(self,command):
        self.seq+=1
        self.sock.sendall(packet(self.seq,2,command))
        req,out=self.receive()
        print(command,"=>",out,flush=True)
        if req!=self.seq: raise AssertionError("RCON request mismatch")
        return out
    def must(self,command,substring):
        got=self.run(command)
        if substring.lower() not in got.lower():
            raise AssertionError(f"Expected {substring!r} from {command}: {got}")

with Rcon() as r:
    r.run("gamerule doMobSpawning false")
    r.run("forceload add 0 0")
    r.run("fill 0 99 0 4 104 4 minecraft:air")
    r.run("fill 0 99 0 4 99 4 minecraft:stone")
    # Shaft output from the creative motor points UP into millstone underside.
    r.must("setblock 2 100 2 create:creative_motor[facing=up] replace","changed")
    r.must("setblock 2 101 2 create:millstone replace","changed")
    r.must("sable mill-inspect 2 101 2","MILL")
    # Ensure the motor actually drives this machine, not just proximity.
    found_speed=False
    for _ in range(30):
        out=r.run("data get block 2 101 2 Speed")
        import re
        vals=re.findall(r"-?\d+(?:\.\d+)?",out)
        if vals and any(abs(float(v))>0 for v in vals):
            found_speed=True
            break
        time.sleep(.5)
    if not found_speed:
        raise AssertionError("Create millstone had no confirmed nonzero kinetic speed")
    # Drop actual entity input on top. Create performs its own item pickup.
    r.must('summon minecraft:item 2.5 102.15 2.5 {Item:{id:"minecraft:wheat",Count:1b},PickupDelay:32767s}',"summoned")
    result=None
    for _ in range(100):
        time.sleep(.75)
        obs=r.run("sable mill-inspect 2 101 2")
        match=re.search(r"flour=(\d+)",obs)
        if match and int(match.group(1))>=1:
            result=obs
            break
    if result is None:
        raise AssertionError("Powered Create millstone did not produce observable wheat flour")
    if "PROCESS_UNVERIFIED NO_RESEARCH_CREDIT" not in result:
        raise AssertionError("Inspector erroneously credited processing to a citizen")
    print("PASS: powered Create millstone produced flour from dropped wheat, no research credit",flush=True)
