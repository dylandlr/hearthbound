#!/usr/bin/env python3
"""Minimal standard-library RCON smoke client for disposable CI world only."""
import os
import socket
import struct
import time

HOST = "127.0.0.1"
PORT = 25575
PASSWORD = os.environ["HEARTHBOUND_RCON_PASSWORD"]

def packet(request_id, packet_type, payload):
    body = struct.pack("<ii", request_id, packet_type) + payload.encode() + b"\x00\x00"
    return struct.pack("<i", len(body)) + body

def recv_exact(sock, count):
    data = b""
    while len(data) < count:
        part = sock.recv(count - len(data))
        if not part:
            raise ConnectionError("RCON socket closed")
        data += part
    return data

def response(sock):
    size = struct.unpack("<i", recv_exact(sock, 4))[0]
    if size < 10 or size > 1000000:
        raise ValueError(f"Unexpected RCON length: {size}")
    body = recv_exact(sock, size)
    req_id, packet_type = struct.unpack("<ii", body[:8])
    return req_id, packet_type, body[8:-2].decode(errors="replace")

with socket.create_connection((HOST, PORT), timeout=15) as sock:
    sock.settimeout(15)
    sock.sendall(packet(1, 3, PASSWORD))
    auth_id, _, _ = response(sock)
    if auth_id != 1:
        # Some servers send an intermediate empty response before authentication.
        auth_id, _, _ = response(sock)
    if auth_id != 1:
        raise RuntimeError("RCON authentication failed")
    for request_id, command, expected in (
        (2, "hearthbound status", "bootstrap active"),
        (3, "sable spawn", "Sable spawned"),
        (4, "execute if entity @e[type=minecraft:villager,name=Sable]", "Test passed"),
    ):
        sock.sendall(packet(request_id, 2, command))
        actual_id, _, output = response(sock)
        print(f"{command}: {output}")
        if actual_id != request_id or expected.lower() not in output.lower():
            raise AssertionError(f"Command failed: {command}; got {output!r}")
    # Controlled test platform in a disposable world. No player inventory used.
    setup = [
        "forceload add 0 0 10 4",
        "fill 0 99 0 10 99 4 minecraft:stone",
        "fill 0 100 0 10 103 4 minecraft:air",
        'setblock 3 100 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:8b}]} replace',
        "setblock 7 100 1 minecraft:chest replace",
        "tp @e[type=minecraft:villager,name=Sable,limit=1] 2 100 1",
        "execute at @e[type=minecraft:villager,name=Sable,limit=1] run sable haul 3 100 1 7 100 1",
    ]
    next_id = 10
    for command in setup:
        sock.sendall(packet(next_id, 2, command))
        got_id, _, output = response(sock)
        print(f"{command}: {output}")
        if got_id != next_id or any(term in output.lower() for term in (
            "unknown command", "incorrect argument", "failed to", "no sable", "not loaded",
            "source already claimed", "cannot")):
            raise AssertionError(f"Setup failed: {command}: {output}")
        if "run sable haul" in command and "sable assigned wheat haul" not in output.lower():
            raise AssertionError(f"Setup failed: {command}: {output}")
        next_id += 1

    # This is a true Minecraft server-side behavior check: inventories must move.
    # It may expose pathfinding or vanilla villager AI interference; failed CI is useful evidence.
    transferred = False
    for i in range(75):
        time.sleep(2)
        sock.sendall(packet(100+i, 2,
            'execute if data block 7 100 1 Items[{id:"minecraft:wheat",Count:1b}]'))
        got_id, _, output = response(sock)
        if got_id == 100+i and "test passed" in output.lower():
            transferred = True
            break
    if not transferred:
        raise AssertionError("Sable did not deliver wheat within 150 seconds")
    sock.sendall(packet(300, 2,
        'execute if data block 3 100 1 Items[{id:"minecraft:wheat",Count:7b}]'))
    got_id, _, output = response(sock)
    if got_id != 300 or "test passed" not in output.lower():
        raise AssertionError("Source count is not 7 wheat after delivery: " + output)
    print("Real server-side wheat transfer verified: source 8->7, destination 0->1")
    # Require physical proximity to destination, not merely inventory mutation.
    sock.sendall(packet(301, 2,
        'execute positioned 7.5 100 1.5 if entity @e[type=minecraft:villager,name=Sable,distance=..2.6]'))
    got_id, _, output = response(sock)
    if got_id != 301 or "test passed" not in output.lower():
        raise AssertionError("Wheat delivered but Sable not near destination: " + output)
    print("Sable proximity verified at destination chest")

print("Hearthbound server commands, entity spawn and wheat hauling verified")
