#!/usr/bin/env python3
"""Actual Create registry + block-entity inspection, not a recipe-completion test."""
import os
import socket
import struct

PASSWORD = os.environ["HEARTHBOUND_RCON_PASSWORD"]

def packet(req, typ, data):
    body = struct.pack("<ii", req, typ) + data.encode() + b"\0\0"
    return struct.pack("<i", len(body)) + body

def recv(sock):
    def exact(n):
        b = b""
        while len(b) < n:
            part = sock.recv(n-len(b))
            if not part:
                raise ConnectionError("RCON closed")
            b += part
        return b
    length = struct.unpack("<i", exact(4))[0]
    body = exact(length)
    return struct.unpack("<i", body[:4])[0], body[8:-2].decode(errors="replace")

with socket.create_connection(("127.0.0.1", 25575), timeout=15) as s:
    s.settimeout(15)
    s.sendall(packet(1, 3, PASSWORD))
    rid, _ = recv(s)
    if rid != 1:
        rid, _ = recv(s)
    assert rid == 1, "RCON authentication failed"
    def command(req, cmd):
        s.sendall(packet(req, 2, cmd))
        rid, output = recv(s)
        print(cmd, "=>", output, flush=True)
        assert rid == req, "Bad RCON response ID"
        return output
    command(2, "forceload add 0 0")
    command(3, "fill 0 99 0 4 99 4 minecraft:stone")
    out = command(4, "setblock 2 100 2 create:millstone replace")
    assert "changed the block" in out.lower(), "Create millstone was not placed"
    out = command(5, "sable mill-inspect 2 100 2")
    assert "MILL OBSERVED" in out or "MILL NO_ITEM_HANDLER" in out, "Millstone not detected"
    assert "MILL NOT_CREATE_MILLSTONE" not in out
    if "MILL OBSERVED" in out:
        assert "PROCESS_UNVERIFIED NO_RESEARCH_CREDIT" in out
    out = command(6, "sable mill-inspect 1 99 1")
    assert "MILL NOT_CREATE_MILLSTONE" in out, "Stone mistaken for millstone"
    print("PASS: real Create block placed, recognized; no false research reward")
