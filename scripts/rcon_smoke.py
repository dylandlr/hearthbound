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

    # Audit is read-only and must expose the actual job identity, endpoints,
    # cargo count and claim ownership from the running world.
    sock.sendall(packet(90, 2,
        'execute at @e[type=minecraft:villager,name=Sable,limit=1] run sable haul-audit'))
    audit_id, _, audit_output = response(sock)
    print("sable haul-audit:", audit_output)
    if audit_id != 90 or any(field not in audit_output for field in (
        "AUDIT job=", "source=", "destination=", "claim=owned",
        "[observations only; no reconciliation performed]")):
        raise AssertionError("Haul audit missing or invalid: " + audit_output)

    # A vanilla chest must NOT masquerade as a processed Create recipe.
    sock.sendall(packet(91, 2, 'sable mill-inspect 3 100 1'))
    mill_id, _, mill_output = response(sock)
    print("sable mill-inspect:", mill_output)
    if mill_id != 91 or "MILL NOT_CREATE_MILLSTONE" not in mill_output:
        raise AssertionError("Mill inspection failed closed incorrectly: " + mill_output)

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

    # End-to-end autonomous progression. A second real chest transfer must
    # happen before study is allowed, and the physical marked book must remain.
    def command(request_id, text):
        sock.sendall(packet(request_id, 2, text))
        got, _, output = response(sock)
        if got != request_id:
            raise AssertionError(f"RCON response mismatch for {text}: {got}")
        print(f"{text}: {output}")
        return output

    book_snbt = ('{Items:[{Slot:0b,id:"minecraft:written_book",Count:1b,'
                 'tag:{"hearthbound.lesson":"hearthbound:basic_milling",'
                 'title:"Hearthbound Milling Primer",author:"Hearthbound",pages:[]}}]}')
    command(400, "setblock 9 100 1 minecraft:chest replace")
    command(401, "setblock 5 100 3 minecraft:chest" + book_snbt + " replace")
    local = "execute at @e[type=minecraft:villager,name=Sable,limit=1] run "
    configured = command(402, local + "sable auto-work-source-discover 9 100 1")
    if "configured discover-source auto work" not in configured.lower():
        raise AssertionError("Autonomous work configuration was rejected: " + configured)
    command(403, local + "sable haul-priority 1")
    command(404, local + "hearthbound library priority 4")
    enabled = command(405, local + "sable auto-work-on")
    if "auto work enabled" not in enabled.lower():
        raise AssertionError("Autonomous work could not be enabled: " + enabled)

    # The configuration contains only the destination, neither the source nor library.
    status = command(406, local + "sable auto-work-status")
    if "discoverLibrary=true" not in status or "discoverSource=true" not in status:
        raise AssertionError("Library discovery mode is not active: " + status)

    # Check actual Minecraft inventory changes, not just the scheduler's
    # decision text. A prior manually delivered item is in the OTHER chest.
    delivered = False
    for i in range(100):
        time.sleep(2)
        found = command(500 + i,
            'execute if data block 9 100 1 Items[{id:"minecraft:wheat",Count:1b}]')
        if "test passed" in found.lower():
            delivered = True
            break
    if not delivered:
        raise AssertionError("Autonomous Sable never delivered wheat to the second chest")
    # Discovery selects the nearest eligible stocked source: the chest at 7
    # contains the wheat delivered by the earlier manual regression.
    remaining = command(610,
        'execute unless data block 7 100 1 Items[{id:"minecraft:wheat"}]')
    if "test passed" not in remaining.lower():
        raise AssertionError("Discovered nearby source did not lose its wheat: " + remaining)
    initial = command(611,
        'execute if data block 3 100 1 Items[{id:"minecraft:wheat",Count:7b}]')
    if "test passed" not in initial.lower():
        raise AssertionError("Distant source unexpectedly changed: " + initial)
    print("Autonomous discovery verified: closest source 7->0, stockpile 0->1; distant source remains 7")

    # The scheduler records completion only after matching its persisted job
    # UUID to a cargo-free COMPLETE state, and only then considers the library.
    verified = False
    for i in range(45):
        time.sleep(2)
        snapshot = command(700 + i, local + "sable auto-work-status")
        if "haulIssued=true" in snapshot and "haulCompleted=true" in snapshot:
            verified = True
            break
    if not verified:
        raise AssertionError("Haul delivery was not recognized by the scheduler")

    # Reading must actually complete inside the running server; the lesson
    # record must be READ_BOOK, not experimental machinery mastery.
    learned = False
    for i in range(100):
        time.sleep(2)
        snapshot = command(800 + i, local + "hearthbound library inspect")
        if ("create:milling/wheat" in snapshot
                and "source=READ_BOOK" in snapshot
                and "LIBRARY_STUDY COMPLETED" in snapshot):
            learned = True
            break
    if not learned:
        raise AssertionError("Sable did not physically finish the milling primer")
    owner = command(910, local + "sable work-owner")
    if "FREE" not in owner:
        raise AssertionError("Citizen owner not released after study: " + owner)
    print("Autonomous HAUL -> verified completion -> STUDY -> knowledge -> FREE passed")

print("Hearthbound server commands, entity spawn and wheat hauling verified")
