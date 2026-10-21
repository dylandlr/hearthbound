#!/usr/bin/env python3
"""Assert client-only roof cutaway did not modify server roof blocks."""
import os
import socket
import struct

def packet(i, kind, message):
    body = struct.pack("<ii", i, kind) + message.encode() + b"\0\0"
    return struct.pack("<i", len(body)) + body

def read(sock):
    def exact(n):
        result = b""
        while len(result) < n:
            segment = sock.recv(n - len(result))
            if not segment:
                raise ConnectionError("RCON disconnected")
            result += segment
        return result
    n = struct.unpack("<i", exact(4))[0]
    if n < 10 or n > 1000000:
        raise ValueError("Bad packet length")
    data = exact(n)
    return struct.unpack("<i", data[:4])[0], data[8:-2].decode(errors="replace")

with socket.create_connection(("127.0.0.1", 25575), timeout=20) as sock:
    sock.settimeout(20)
    sock.sendall(packet(1, 3, os.environ["HEARTHBOUND_RCON_PASSWORD"]))
    rid, _ = read(sock)
    if rid != 1:
        rid, _ = read(sock)
    if rid != 1:
        raise RuntimeError("RCON authentication failed")
    for i, (x, z) in enumerate(((4, 4), (6, 6), (8, 8), (3, 7)), 10):
        command = f"execute if block {x} 105 {z} minecraft:spruce_planks"
        sock.sendall(packet(i, 2, command))
        response_id, response = read(sock)
        print(f"ROOF_INTEGRITY {x} 105 {z}: {response}", flush=True)
        if response_id != i or "test passed" not in response.lower():
            raise AssertionError(f"Roof block was changed or missing: {command}: {response}")
print("ROOF_INTEGRITY_SERVER_PASS", flush=True)
