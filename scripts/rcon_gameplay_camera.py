#!/usr/bin/env python3
"""Place the real connected capture player overlooking the Create experiment."""
import os
import socket
import struct

def pkt(i,t,s):
    b=struct.pack("<ii",i,t)+s.encode()+b"\0\0"
    return struct.pack("<i",len(b))+b

def receive(sock):
    def exact(n):
        data=b""
        while len(data)<n:
            part=sock.recv(n-len(data))
            if not part: raise ConnectionError("RCON closed")
            data+=part
        return data
    n=struct.unpack("<i",exact(4))[0]
    if not 10<=n<=1000000: raise ValueError("RCON packet invalid")
    b=exact(n)
    return struct.unpack("<i",b[:4])[0],b[8:-2].decode(errors="replace")

with socket.create_connection(("127.0.0.1",25575),timeout=20) as sock:
    sock.settimeout(20)
    sock.sendall(pkt(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
    rid,_=receive(sock)
    if rid!=1: rid,_=receive(sock)
    if rid!=1: raise RuntimeError("Camera RCON auth failed")
    commands=[
        "time set noon",
        "weather clear",
        "gamemode spectator HB_Camera",
        "tp HB_Camera 11 105 9 facing 6 101 1",
        "effect give HB_Camera minecraft:night_vision 600 0 true",
    ]
    for i,command in enumerate(commands,10):
        sock.sendall(pkt(i,2,command))
        rid,reply=receive(sock)
        print(command,"=>",reply,flush=True)
        if rid!=i or any(x in reply.lower() for x in
                ("unknown command","no entity","no player was found","failed to","incorrect argument")):
            raise AssertionError("Camera setup failure: "+command+" => "+reply)
