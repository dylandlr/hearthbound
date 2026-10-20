#!/usr/bin/env python3
"""Remove temporary camera-demo citizens without touching real colony citizens."""
import os
import socket
import struct

def packet(i, kind, command):
    body = struct.pack("<ii", i, kind) + command.encode() + b"\0\0"
    return struct.pack("<i", len(body)) + body

def read(sock):
    def exact(n):
        out = b""
        while len(out) < n:
            chunk = sock.recv(n-len(out))
            if not chunk:
                raise ConnectionError("RCON disconnected")
            out += chunk
        return out
    size = struct.unpack("<i", exact(4))[0]
    if size < 10 or size > 1000000:
        raise ValueError("Invalid packet")
    b = exact(size)
    return struct.unpack("<i", b[:4])[0], b[8:-2].decode(errors="replace")

with socket.create_connection(("127.0.0.1", 25575), timeout=20) as sock:
    sock.settimeout(20)
    sock.sendall(packet(1, 3, os.environ["HEARTHBOUND_RCON_PASSWORD"]))
    rid, _ = read(sock)
    if rid != 1:
        rid, _ = read(sock)
    if rid != 1:
        raise RuntimeError("RCON auth failed")
    command = "kill @e[type=minecraft:villager,tag=hb_camera_fixture]"
    sock.sendall(packet(2, 2, command))
    response_id, result = read(sock)
    if response_id != 2:
        raise RuntimeError("RCON reply mismatched")
    print(f"{command} => {result}", flush=True)
