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
    # The temporary player-control fixture includes a second Create millstone.
    # Remove it before autonomous research: local discovery otherwise chooses
    # the nearer unpowered fixture mill instead of the powered test mill.
    # The fixture owns this exact block, so do not alter real colony machines.
    cleanup = "setblock 3 101 5 minecraft:air replace"
    sock.sendall(packet(3, 2, cleanup))
    cleanup_id, cleanup_output = read(sock)
    print(f"{cleanup} => {cleanup_output}", flush=True)
    if cleanup_id != 3 or "could not set" in cleanup_output.lower():
        raise RuntimeError("Failed to remove disposable camera fixture millstone")
    verify = "execute unless block 3 101 5 create:millstone"
    sock.sendall(packet(4, 2, verify))
    verify_id, verify_output = read(sock)
    print(f"{verify} => {verify_output}", flush=True)
    if verify_id != 4 or "test passed" not in verify_output.lower():
        raise RuntimeError("Disposable camera millstone still exists")

