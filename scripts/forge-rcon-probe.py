#!/usr/bin/env python3
"""Minimal local RCON client for disposable Forge CI server; Python stdlib only."""
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
        conn.sendall(packet(11, 3, "hearthbound-ci-only-password"))
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

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "after-restart":
        restored = execute("hearthbound ci_restart_check")
        print(restored)
        if "HB_RESTART_PASS" not in restored:
            raise AssertionError("Saved cargo did not survive reboot: " + restored)
        unblocked = execute("hearthbound ci_restart_unblock")
        print(unblocked)
        if "HB_RESTART_UNBLOCKED" not in unblocked:
            raise AssertionError("Failed to unblock recovered delivery")
        for n in range(70):
            time.sleep(1)
            result = execute("hearthbound ci_restart_delivered")
            if "HB_RESTART_DELIVERED" in result:
                print(result)
                break
            if "HB_RESTART_PENDING" not in result:
                raise AssertionError("Recovered delivery failed: " + result)
        else:
            raise AssertionError("Recovery delivery timed out: " + result)
        # Keep ticking after completion: the persisted cargo must not be replayed.
        time.sleep(3)
        stable = execute("hearthbound ci_restart_delivered")
        if "HB_RESTART_DELIVERED" not in stable:
            raise AssertionError("Delivery was not stable after completion: " + stable)
        print("HB_RESTART_NO_REPLAY_PASS source=4 dest=4 cargo=0", flush=True)
        sys.exit(0)
    # Let Minecraft enter its empty-server entity-idle state before dispatch.
    # The disposable arena must explicitly provide its own ticking tickets.
    print("Idling playerless server for 20s before dispatch", flush=True)
    time.sleep(20)
    for attempt in range(30):
        try:
            create = execute("hearthbound create_status")
            print(create)
            if "installed=false" not in create:
                raise AssertionError("Expected optional Create absence on vanilla Forge test runner")
            result = execute("hearthbound ci_probe")
            print(result)
            if "HB_CI_PROBE_PASS" not in result:
                raise AssertionError("Real Forge command did not report success")
            haul = execute("hearthbound ci_haul_probe")
            print(haul)
            if "HB_HAUL_SETUP_PASS" not in haul:
                raise AssertionError("Real Forge hauling baseline failed")
            print("PASS: real-world Forge entity and inventory setup probes")
            assert "HB_HAUL_E2E_STARTED" in execute("hearthbound ci_haul_start")
            for n in range(70):
                time.sleep(1)
                state = execute("hearthbound ci_haul_check")
                if "HB_HAUL_E2E_FAIL" in state:
                    raise AssertionError("Hauling failed: " + state)
                if "HB_HAUL_E2E_PASS" in state:
                    print(state)
                    break
            else:
                raise AssertionError("Hauling did not finish: " + state)
            # Start atop the source: extraction must wait until the worker steps
            # to an accessible side, and delivery must happen beside its barrel.
            assert "HB_HAUL_E2E_STARTED" in execute("hearthbound ci_station_approach_start")
            for n in range(70):
                time.sleep(1)
                approach = execute("hearthbound ci_haul_check")
                if "HB_HAUL_E2E_FAIL" in approach:
                    raise AssertionError("Station approach failed: " + approach)
                if "HB_HAUL_E2E_PASS" in approach and "approachedBeside=true" in approach:
                    print("HB_STATION_APPROACH_PASS " + approach, flush=True)
                    break
            else:
                raise AssertionError("Station approach timed out: " + approach)
            assert "HB_HAUL_E2E_STARTED" in execute("hearthbound ci_haul_full_start")
            for n in range(30):
                time.sleep(1)
                full_state = execute("hearthbound ci_haul_check")
                if "HB_HAUL_FULL_PASS" in full_state:
                    print(full_state)
                    break
            else:
                raise AssertionError("Full destination test did not pass: " + full_state)
            assert "HB_HAUL_E2E_STARTED" in execute("hearthbound ci_haul_block_after_pickup")
            for n in range(50):
                time.sleep(1)
                blocked = execute("hearthbound ci_haul_check")
                if "HB_HAUL_CARGO_BLOCKED_PASS" in blocked:
                    print(blocked)
                    break
            else:
                raise AssertionError("Post-pickup blockage test failed: " + blocked)
            assert "HB_HAUL_E2E_STARTED" in execute("hearthbound ci_restart_stage")
            for n in range(50):
                time.sleep(1)
                stage = execute("hearthbound ci_haul_check")
                if n in (0, 4, 9, 19, 34, 49):
                    print("Restart staging", n, stage, flush=True)
                if "HB_HAUL_CARGO_BLOCKED_PASS" in stage:
                    print("HB_RESTART_STAGED")
                    break
            else:
                raise AssertionError("Restart cargo staging failed: " + stage)
            print(execute("save-all flush"))
            print(execute("stop"))
            sys.exit(0)
        except (OSError, TimeoutError) as exc:
            if attempt == 29:
                raise
            time.sleep(2)
    sys.exit(1)
