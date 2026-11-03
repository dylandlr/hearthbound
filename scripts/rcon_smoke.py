#!/usr/bin/env python3
"""Minimal standard-library RCON smoke client for disposable CI world only."""
import os
import socket
import struct
import time

HOST = "127.0.0.1"
PORT = 25575
PASSWORD = os.environ["HEARTHBOUND_RCON_PASSWORD"]
TRIAL_MODE = os.environ.get("HEARTHBOUND_TRIAL_MODE", "TRAINED_MLP").upper()
if TRIAL_MODE not in ("SCRIPTED", "TRAINED_MLP"):
    raise ValueError("HEARTHBOUND_TRIAL_MODE must be SCRIPTED or TRAINED_MLP")

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

def response(sock, allow_empty=False):
    # Minecraft's RCON can emit trailing/empty RESPONSE_VALUE frames. A
    # one-frame-per-command assumption can misattribute an empty frame from
    # command N to command N+1. Skip blanks for commands, never for auth.
    for _ in range(24):
        size = struct.unpack("<i", recv_exact(sock, 4))[0]
        if size < 10 or size > 1000000:
            raise ValueError(f"Unexpected RCON length: {size}")
        body = recv_exact(sock, size)
        req_id, packet_type = struct.unpack("<ii", body[:8])
        output = body[8:-2].decode(errors="replace")
        if output.strip() or allow_empty:
            return req_id, packet_type, output
    raise RuntimeError("RCON returned 24 consecutive empty response frames")

with socket.create_connection((HOST, PORT), timeout=15) as sock:
    sock.settimeout(15)
    sock.sendall(packet(1, 3, PASSWORD))
    auth_id, _, _ = response(sock, allow_empty=True)
    if auth_id != 1:
        # Some servers send an intermediate empty response before authentication.
        auth_id, _, _ = response(sock, allow_empty=True)
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

    # Probe a REAL Create block registered in the running Forge world.
    # This does not claim powered processing or wheat-to-flour success.
    sock.sendall(packet(92, 2, "setblock 9 100 3 create:millstone replace"))
    block_id, _, block_output = response(sock)
    print("create millstone placement:", block_output)
    if block_id != 92 or "changed the block" not in block_output.lower():
        raise AssertionError("Create millstone could not be placed: " + block_output)

    sock.sendall(packet(93, 2, "sable mill-inspect 9 100 3"))
    inspect_id, _, inspect_output = response(sock)
    print("real Create mill inspection:", inspect_output)
    if inspect_id != 93 or "NOT_CREATE_MILLSTONE" in inspect_output or "MILL" not in inspect_output:
        raise AssertionError("Real Create millstone was not recognized: " + inspect_output)

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



    # Shared read-only comparison of both policy modes on one real server state.
    def compare_shadow(stage, expected):
        results = {}
        for mode in ("SCRIPTED", "TRAINED_MLP"):
            output = checked("hearthbound policy_shadow 9 100 3 " + mode,
                             stage + " " + mode + " shadow")
            if ("shadow_mode=" + mode) not in output or "EXECUTION_DISABLED" not in output:
                raise AssertionError("Invalid live shadow observation " + stage + ": " + output)
            if "selected_action=" + expected not in output:
                raise AssertionError("Unexpected " + mode + " on " + stage + ": " + output)
            results[mode] = output
        # GitHub truncates very long console lines. Audit both full RCON
        # responses here, then emit one compact, parseable evidence record.
        def value(text, key):
            import re
            found = re.search(r"(?:^|\s)" + re.escape(key) + r"=([^\s]+)", text)
            if not found:
                raise AssertionError("Missing shadow field " + key + ": " + text)
            return found.group(1)
        for field in ("citizen", "pos", "powered", "wheat", "flour", "blocked", "experience"):
            if value(results["SCRIPTED"], field) != value(results["TRAINED_MLP"], field):
                raise AssertionError("Shadow policies observed different " + field)
        for mode,output in results.items():
            if value(output, "selected_action") != expected or value(output,"shadow_mode") != mode:
                raise AssertionError("Invalid shadow result: " + output)
        trained=results["TRAINED_MLP"]
        print("LIVE_SHADOW_PAIR stage=" + stage + " expected=" + expected
              + " scripted=" + value(results["SCRIPTED"], "selected_action")
              + " trained=" + value(trained, "selected_action")
              + " raw_mlp=" + value(trained,"mlp_action")
              + " citizen=" + value(trained,"citizen")
              + " powered=" + value(trained,"powered")
              + " wheat=" + value(trained,"wheat")
              + " flour=" + value(trained,"flour")
              + " blocked=" + value(trained,"blocked")
              + " experience=" + value(trained,"experience")
              + " disagreement=" + value(trained,"model_disagreement")
              + " masked=" + value(trained,"action_masked")
              + " read_only=true")
        return results

    # Experimental real Create processing probe (separate from citizen learning).
    # Motor -> vertical shaft -> millstone. Failure must fail CI, not be called success.
    print("Beginning powered millstone wheat-to-flour acceptance probe")
    def checked(command, label, require=None):
        global next_id
        sock.sendall(packet(next_id, 2, command))
        received, _, output = response(sock)
        print(f"{label}: {output}")
        if received != next_id or (require and require.lower() not in output.lower()):
            raise AssertionError(f"{label} failed: {output!r}")
        next_id += 1
        return output

    checked("setblock 9 98 3 create:creative_motor[facing=up] replace",
            "creative motor", "changed the block")
    checked("setblock 9 99 3 create:shaft[axis=y] replace",
            "vertical shaft", "changed the block")
    # The earlier machine-recognition probe already placed this block.
    # Verify it remains the real Create millstone after shaft/motor installation.
    verified = checked("sable mill-inspect 9 100 3", "powered millstone exists")
    if "MILL OBSERVED" not in verified or "block=create:millstone" not in verified:
        raise AssertionError("Powered fixture lost its Create millstone: " + verified)
    # Forge/Create kinetic state is updated on subsequent server ticks, not
    # synchronously by the RCON block placement command. Never fake readiness.
    import re
    power_ready = False
    for attempt in range(45):
        probe = checked("hearthbound policy_probe 9 100 3",
                        f"live empty mill power readiness {attempt}")
        if "EXECUTION_DISABLED" not in probe:
            raise AssertionError("Policy probe unexpectedly attempted execution: " + probe)
        if "action=REQUEST_WHEAT_HAUL" in probe and "powered=true" in probe:
            power_ready = True
            if "mlp_action=REQUEST_WHEAT_HAUL" not in probe or "ML_INFERENCE_READ_ONLY" not in probe:
                raise AssertionError("Trained MLP disagrees with empty powered mill: " + probe)
            compare_shadow("empty_powered", "REQUEST_WHEAT_HAUL")
            print("LIVE_CREATE_POWER_CONFIRMED " + probe)
            break
        if "action=INSPECT_UNPOWERED" not in probe or "powered=false" not in probe:
            raise AssertionError("Unexpected pre-production policy state: " + probe)
        time.sleep(1)
    if not power_ready:
        raise AssertionError("CREATE_POWER_NOT_READY: millstone remained unpowered after 45s")
    checked("summon minecraft:item 9.5 101.2 3.5 {Item:{id:\"minecraft:wheat\",Count:1b},PickupDelay:32767s}",
            "wheat dropped onto real millstone", "summoned")
    flour_observed = False
    for i in range(90):
        time.sleep(2)
        result = checked("sable mill-inspect 9 100 3", f"milling sample {i}")
        import re
        flour = re.search(r"\bflour=(\d+)", result)
        if flour and int(flour.group(1)) > 0:
            flour_observed = True
            print("REAL_CREATE_FLOUR_OBSERVED " + result)
            break
    if not flour_observed:
        raise AssertionError("NO_REAL_CREATE_PRODUCTION: did not observe flour in 180s")
    probe = checked("hearthbound policy_probe 9 100 3", "finished mill policy probe")
    if "action=COLLECT_OUTPUT" not in probe:
        raise AssertionError("Live policy probe did not recognize finished Create product: " + probe)
    if "mlp_action=COLLECT_OUTPUT" not in probe or "ML_INFERENCE_READ_ONLY" not in probe:
        raise AssertionError("Trained MLP failed to recognize finished output: " + probe)
    compare_shadow("output_ready", "COLLECT_OUTPUT")



    # Separate trial: actual citizen delivery to a clean, reserved Create millstone.
    # The motor-only run above deliberately earns no research credit or citizen memory.
    print("Beginning Sable-authored wheat milling trial")
    checked("setblock 9 100 3 minecraft:air replace", "clear prior machine", "changed the block")
    checked("setblock 9 100 3 create:millstone replace", "fresh millstone", "changed the block")
    checked('setblock 8 100 1 minecraft:chest replace',
            "citizen empty wheat source", "changed the block")
    checked("tp @e[type=minecraft:villager,name=Sable,limit=1] 7 100 1",
            "position Sable near the mill", "teleported")
    # Newly rebuilt Create mill can require a few server ticks for kinetic power.
    for ready_attempt in range(45):
        observed = checked("hearthbound policy_probe 9 100 3",
                           f"policy dispatch power check {ready_attempt}")
        if "powered=true" in observed and "action=REQUEST_WHEAT_HAUL" in observed:
            break
        if "powered=false" not in observed:
            raise AssertionError("Unexpected live world state before policy dispatch: "+observed)
        time.sleep(1)
    else:
        raise AssertionError("Policy dispatch mill never became powered")
    # Controlled shortage: no wheat exists in the source chest. This MUST be
    # rejected by the real server without a new hauling assignment or credit.
    shortage = checked("hearthbound policy_trial 8 100 1 9 100 3 " + TRIAL_MODE,
                       "real source shortage rejection")
    if "Source inventory has no real wheat" not in shortage:
        raise AssertionError("Missing-wheat trial was not explicitly rejected: " + shortage)
    idle_audit = checked(
        'execute at @e[type=minecraft:villager,name=Sable,limit=1] run sable haul-audit',
        "no new hauling job after shortage")
    if "status=Haul complete" not in idle_audit:
        raise AssertionError("Shortage may have created or changed a hauling task: " + idle_audit)
    print("REAL_POLICY_TRIAL_REJECTION mode=" + TRIAL_MODE
          + " reason=SOURCE_NO_WHEAT dispatched=false"
          + " credit=0 existing_job_unchanged=true")
    checked('setblock 8 100 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:1b}]} replace',
            "restored trial source wheat", "changed the block")

    before_time = checked("time query gametime", "trial start server game time")
    start_time_values = re.findall(r"\d+", before_time)
    if not start_time_values:
        raise AssertionError("No authoritative Minecraft start game time: " + before_time)
    trial_start_tick = int(start_time_values[-1])
    assignment = checked(
        "hearthbound policy_trial 8 100 1 9 100 3 " + TRIAL_MODE,
        "one-shot policy hauling dispatch " + TRIAL_MODE)
    if "POLICY_TRIAL_ASSIGNED" not in assignment or ("mode=" + TRIAL_MODE) not in assignment:
        raise AssertionError("Policy did not dispatch authorized Sable task: " + assignment)
    print("REAL_POLICY_SELECTED_SABLE_HAUL mode=" + TRIAL_MODE, assignment)
    import re
    matched = False
    for i in range(90):
        time.sleep(2)
        audit = checked(
            'execute at @e[type=minecraft:villager,name=Sable,limit=1] run sable haul-audit',
            f"authorized mill audit {i}")
        mill = checked("sable mill-inspect 9 100 3", f"authorized mill sample {i}")
        memory = checked(
            'data get entity @e[type=minecraft:villager,name=Sable,limit=1] ForgeData."hearthbound.verifiedMillExperience.v1".observedVerifiedProcesses',
            f"citizen experiment memory {i}")
        if re.search(r"\bflour=[1-9]\d*", mill) and re.search(r"\b1L\b", memory):
            print("REAL_CITIZEN_EXPERIENCE_OBSERVED", audit, mill, memory)
            probe = checked("hearthbound policy_probe 9 100 3",
                            "live trained-policy input probe after verified citizen experiment")
            if "mlp_action=COLLECT_OUTPUT" not in probe or "model=mill-mlp-v1" not in probe:
                raise AssertionError("Trained MLP did not load for experienced citizen: " + probe)
            if "experience=1" not in probe or "policy=scripted_reference" not in probe:
                raise AssertionError("Live policy probe cannot observe verified Sable experience: " + probe)
            end_time = checked("time query gametime", "trial completed server game time")
            end_time_values = re.findall(r"\d+", end_time)
            if not end_time_values:
                raise AssertionError("No authoritative Minecraft completion game time: " + end_time)
            elapsed = int(end_time_values[-1]) - trial_start_tick
            if elapsed < 0:
                raise AssertionError("World game time decreased during policy experiment")
            print("REAL_POLICY_TRIAL_RESULT mode=" + TRIAL_MODE
                  + " completion=1 elapsed_ticks=" + str(elapsed)
                  + " verified_experience=1 flour_observed=1"
                  + " executor=SableHauling")

            results=compare_shadow("citizen_experienced", "COLLECT_OUTPUT")
            for value in results.values():
                if "experience=1" not in value:
                    raise AssertionError("Shadow policy did not read persistent experience: " + value)

            matched = True
            break
    if not matched:
        raise AssertionError("NO_AUTHORIZED_CITIZEN_MILL_EXPERIENCE: no matching flour and persisted citizen memory within 180 seconds")

print("Hearthbound server commands, entity spawn and wheat hauling verified")
