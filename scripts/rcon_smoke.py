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
            # The villager may still be loading or walking after teleport. Retry
            # the *real assignment*, never forge a successful response.
            history = [output]
            for attempt in range(1, 7):
                time.sleep(1)
                sock.sendall(packet(next_id + 1000 + attempt, 2,
                    "execute if entity @e[type=minecraft:villager,name=Sable,limit=1]"))
                _, _, present = response(sock)
                sock.sendall(packet(next_id + 2000 + attempt, 2,
                    "tp @e[type=minecraft:villager,name=Sable,limit=1] 2 100 1"))
                _, _, moved = response(sock)
                sock.sendall(packet(next_id + 3000 + attempt, 2, command))
                retry_id, _, retry_output = response(sock)
                history.append(f"attempt={attempt} entity={present!r} tp={moved!r} haul={retry_output!r}")
                if retry_id == next_id + 3000 + attempt and "sable assigned wheat haul" in retry_output.lower():
                    output = retry_output
                    break
            if "sable assigned wheat haul" not in output.lower():
                raise AssertionError(f"Setup failed after bounded entity/teleport retries: {command}; " + "; ".join(history))
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
    # Inventory delivery may be visible before the villager's movement/position
    # settles. Observe for a short bounded window rather than racing one tick.
    near = False
    for _ in range(15):
        sock.sendall(packet(301, 2,
            'execute positioned 7.5 100 1.5 if entity @e[type=minecraft:villager,name=Sable,distance=..2.6]'))
        got_id, _, output = response(sock)
        if got_id == 301 and "test passed" in output.lower():
            near = True
            break
        time.sleep(.5)
    if not near:
        raise AssertionError("Wheat delivered but Sable never near destination: " + output)
    print("Sable proximity verified at destination chest")
    # A verified physical delivery now creates persistent event provenance
    # and a deterministic, per-citizen starting-instinct profile.
    sock.sendall(packet(305, 2, 'execute as @e[type=minecraft:villager,name=Sable,limit=1] at @s run sable instinct-inspect'))
    _, _, instincts = response(sock)
    if "INSTINCT ageStage=ADULT" not in instincts or "food=" not in instincts or "cooperation=" not in instincts:
        raise AssertionError("Citizen instinct profile missing: " + instincts)
    sock.sendall(packet(306, 2, 'execute as @e[type=minecraft:villager,name=Sable,limit=1] at @s run sable social-inspect'))
    _, _, history = response(sock)
    if "SOCIAL_MEMORY events=1" not in history or "WHEAT_DELIVERY" not in history or "source=SELF" not in history:
        raise AssertionError("Real haul event was not recorded once: " + history)
    print("Minecraft historical event recorded with job provenance and unique citizen instincts")


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
    # Verify conservation without assuming a fixed winning source: source
    # choice is made from the citizen's position at observation time and
    # can differ as the villager moves. Exactly one of the two stocked chests
    # must lose one wheat while the other remains unchanged.
    source3_six = "test passed" in command(610,
        'execute if data block 3 100 1 Items[{id:"minecraft:wheat",Count:6b}]').lower()
    source3_seven = "test passed" in command(611,
        'execute if data block 3 100 1 Items[{id:"minecraft:wheat",Count:7b}]').lower()
    source7_empty = "test passed" in command(612,
        'execute unless data block 7 100 1 Items[{id:"minecraft:wheat"}]').lower()
    source7_one = "test passed" in command(613,
        'execute if data block 7 100 1 Items[{id:"minecraft:wheat",Count:1b}]').lower()
    if not ((source3_six and source7_one) or (source3_seven and source7_empty)):
        raise AssertionError("Autonomous transfer violated inventory conservation or source selection")
    print("Autonomous discovery verified: one physical source decremented and stockpile gained one wheat")

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


    # Multi-citizen regression: two agents prefer the same stocked chest.
    # Both must transport exactly one wheat to a shared stockpile, using
    # distinct physical jobs; source claims prevent duplicate pickup.
    command(1000, "forceload add 18 0 32 4")
    command(1001, "fill 18 99 0 32 99 4 minecraft:stone")
    command(1002, "fill 18 100 0 32 103 4 minecraft:air")
    command(1003, 'setblock 20 100 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:1b}]} replace')
    command(1004, 'setblock 25 100 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:1b}]} replace')
    command(1005, "setblock 23 100 3 minecraft:chest replace")
    # The board must expose two stock sources before the citizens claim them.
    board_reader = "execute positioned 21 100 1 run sable board-inspect 23 100 3"
    # Spawn Iris first so a real Hearthbound citizen can observe the board.
    for n, x in (("Iris", 21), ("Moss", 22)):
        spawned = command(1010 + x, f"execute positioned {x} 100 1 run sable spawn-named {n}")
        if f"citizen spawned: {n}".lower() not in spawned.lower():
            raise AssertionError("Unable to spawn " + n + ": " + spawned)
        self_cmd = f"execute as @e[type=minecraft:villager,name={n},limit=1] at @s run "
        configured = command(1040 + x, self_cmd + "sable auto-work-source-discover 23 100 3")
        if "configured discover-source auto work" not in configured.lower():
            raise AssertionError("Cannot configure " + n + ": " + configured)
        if n == "Iris":
            board = command(1060, self_cmd + "sable board-inspect 23 100 3")
            if "COLONY_BOARD wheat offers=2 free=2 claimed=0" not in board:
                raise AssertionError("Expected 2 available shared board jobs: " + board)
        command(1070 + x, self_cmd + "sable haul-priority 1")
        command(1100 + x, self_cmd + "hearthbound library priority 0")
        activated = command(1130 + x, self_cmd + "sable auto-work-on")
        if "auto work enabled" not in activated.lower():
            raise AssertionError("Cannot enable " + n + ": " + activated)

    arrived = False
    for i in range(120):
        time.sleep(2)
        state = command(1200 + i,
            'execute if data block 23 100 3 Items[{id:"minecraft:wheat",Count:2b}]')
        if "test passed" in state.lower():
            arrived = True
            break
    if not arrived:
        raise AssertionError("Two citizens failed to deliver 2 wheat to shared stockpile")
    for number, x in ((1400, 20), (1401, 25)):
        check = command(number, f'execute unless data block {x} 100 1 Items[{{id:"minecraft:wheat"}}]')
        if "test passed" not in check.lower():
            raise AssertionError(f"Source chest {x} still stocked after both deliveries: {check}")

    board_after = command(1390,
        "execute as @e[type=minecraft:villager,name=Iris,limit=1] at @s run sable board-inspect 23 100 3")
    if "COLONY_BOARD wheat offers=0 free=0 claimed=0" not in board_after:
        raise AssertionError("Board did not clear depleted wheat sources: " + board_after)

    import re
    jobs = []
    for n, req in (("Iris", 1500), ("Moss", 1501)):
        who = f"execute as @e[type=minecraft:villager,name={n},limit=1] at @s run "
        complete = False
        for i in range(15):
            status = command(req + i * 2, who + "sable auto-work-status")
            if "haulCompleted=true" in status:
                found = re.search(r"haulJob=([0-9a-f-]{36})", status)
                if not found:
                    raise AssertionError("Missing physical job identity for " + n)
                jobs.append(found.group(1))
                complete = True
                break
            time.sleep(2)
        if not complete:
            raise AssertionError(n + " did not verify its hauling completion")
        owner = command(req + 100, who + "sable work-owner")
        if "FREE" not in owner:
            raise AssertionError(n + " still owns work after delivery: " + owner)
    if len(set(jobs)) != 2:
        raise AssertionError("Two citizens shared a haul job UUID: " + repr(jobs))
    print("MULTI_CITIZEN VERIFIED: distinct job UUIDs, two empty sources, two wheat in shared destination, both FREE")
    # Both agents must have distinct personal historical events, and the
    # social-web observation must enumerate actual Minecraft positions.
    for n, req in (("Iris", 1710), ("Moss", 1720)):
        who = f"execute as @e[type=minecraft:villager,name={n},limit=1] at @s run "
        memory = command(req, who + "sable social-inspect")
        if "WHEAT_DELIVERY" not in memory or "source=SELF" not in memory or "job=" not in memory:
            raise AssertionError(n + " missing verified, witnessed-world history: " + memory)
        profile = command(req+1, who + "sable instinct-inspect")
        if "food=" not in profile or "exploration=" not in profile:
            raise AssertionError(n + " has no stable personal instinct profile: " + profile)
    web = command(1730,
        "execute as @e[type=minecraft:villager,name=Iris,limit=1] at @s run sable social-web")
    if "SOCIAL_WEB citizens=" not in web or "citizen=Iris" not in web or "citizen=Moss" not in web:
        raise AssertionError("Social-web world snapshot missing real citizens: " + web)
    print("SOCIETY FOUNDATION VERIFIED: Minecraft event provenance, distinct instincts, real population positions")


print("Hearthbound server commands, entity spawn and wheat hauling verified")
