#!/usr/bin/env python3
"""Minimal local RCON client for disposable Forge CI server; Python stdlib only."""
import os
import socket
import struct
import sys
import time

def packet(request_id, kind, message):
    payload = struct.pack("<ii", request_id, kind) + message.encode() + b"\0\0"
    return struct.pack("<i", len(payload)) + payload

def recv_exact(sock, size):
    result = b""
    while len(result) < size:
        data = sock.recv(size - len(result))
        if not data:
            raise ConnectionError("RCON socket closed")
        result += data
    return result

def recv_packet(sock):
    length = struct.unpack("<i", recv_exact(sock, 4))[0]
    if length < 10 or length > 65536:
        raise ValueError("Bad RCON packet")
    raw = recv_exact(sock, length)
    request_id, kind = struct.unpack("<ii", raw[:8])
    return request_id, kind, raw[8:-2].decode(errors="replace")

def execute(command):
    with socket.create_connection(("127.0.0.1", 25575), timeout=5) as conn:
        conn.settimeout(10)
        conn.sendall(packet(11, 3, os.environ.get("HEARTHBOUND_RCON_PASSWORD", "hearthbound-ci-only-password")))
        for _ in range(3):
            rid, _, _ = recv_packet(conn)
            if rid == -1:
                raise PermissionError("RCON authentication failed")
            if rid == 11:
                break
        conn.sendall(packet(12, 2, command))
        rid, _, response = recv_packet(conn)
        if rid != 12:
            raise RuntimeError(f"Unexpected response id: {rid}")
        return response

