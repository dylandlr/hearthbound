#!/usr/bin/env python3
"""Two-phase real Forge restart test. Run with 'prepare' then 'verify'.

Disposable CI world only. Requires HEARTHBOUND_RCON_PASSWORD.
A graceful save/restart checks persisted cargo recovery; it does not simulate
a power loss mid-inventory-write.
"""
import os
import socket
import struct
import sys
import time

HOST = "127.0.0.1"
PORT = 25575
PASSWORD = os.environ["HEARTHBOUND_RCON_PASSWORD"]
VILLAGER = '@e[type=minecraft:villager,name=Sable,limit=1]'
SOURCE = 'execute if data block 3 100 1 Items[{id:"minecraft:wheat",Count:7b}]'
EMPTY_DEST = 'execute unless data block 32 100 1 Items[{id:"minecraft:wheat"}]'
CARGO = 'execute if data entity ' + VILLAGER + ' ForgeData."hearthbound.haul".cargo'

def packet(request_id, packet_type, payload):
    body = struct.pack("<ii", request_id, packet_type) + payload.encode() + b"\x00\x00"
    return struct.pack("<i", len(body)) + body

def recv_exact(sock, count):
    data = b""
    while len(data) < count:
        part = sock.recv(count - len(data))
        if not part:
            raise ConnectionError("RCON connection closed")
        data += part
    return data

def response(sock):
    size = struct.unpack("<i", recv_exact(sock, 4))[0]
    if size < 10 or size > 1000000:
        raise ValueError("Bad RCON packet size " + str(size))
    body = recv_exact(sock, size)
    return struct.unpack("<ii", body[:8])[0], body[8:-2].decode(errors="replace")

class Rcon:
    def __enter__(self):
        self.sock = socket.create_connection((HOST, PORT), timeout=20)
        self.sock.settimeout(20)
        self.request = 10
        self.sock.sendall(packet(1, 3, PASSWORD))
        rid, _ = response(self.sock)
        if rid != 1:
            rid, _ = response(self.sock)
        if rid != 1:
            raise RuntimeError("RCON login failed")
        return self

    def __exit__(self, *_):
        self.sock.close()

    def run(self, command):
        self.request += 1
        self.sock.sendall(packet(self.request, 2, command))
        rid, output = response(self.sock)
        if rid != self.request:
            raise RuntimeError(f"Response ID mismatch on {command}: {rid}")
        print(f"{command} -> {output}", flush=True)
        return output

    def must_pass(self, command):
        output = self.run(command)
        if "test passed" not in output.lower():
            raise AssertionError(f"Expected test passed: {command}, got {output!r}")

def prepare():
    with Rcon() as r:
        for command in [
            "gamerule doMobSpawning false",
            "forceload add 0 0 34 4",
            "fill 0 99 0 34 99 4 minecraft:stone",
            "fill 0 100 0 34 103 4 minecraft:air",
            'setblock 3 100 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:8b}]} replace',
            "setblock 32 100 1 minecraft:chest replace",
            "sable spawn",
            f"tp {VILLAGER} 2 100 1",
            f"execute at {VILLAGER} run sable haul 3 100 1 32 100 1",
        ]:
            result = r.run(command)
            if any(error in result.lower() for error in ("unknown command", "incorrect argument", "no sable", "cannot", "failed to")):
                raise AssertionError(f"Setup failed: {command}: {result}")
        deadline = time.monotonic() + 100
        while time.monotonic() < deadline:
            a = r.run(SOURCE)
            b = r.run(CARGO)
            c = r.run(EMPTY_DEST)
            if all("test passed" in x.lower() for x in (a,b,c)):
                print("CONFIRMED: 7 wheat at source, Sable carrying 1, destination empty")
                r.run("save-all flush")
                # Reassert that destination did not receive cargo before stop.
                r.must_pass(EMPTY_DEST)
                r.must_pass(CARGO)
                r.run("stop")
                return
            time.sleep(0.5)
        raise AssertionError("Sable never reached in-transit cargo state before timeout")

def verify():
    with Rcon() as r:
        deadline = time.monotonic() + 60
        quarantined = False
        while time.monotonic() < deadline:
            output = r.run(f"execute at {VILLAGER} run sable haul-status")
            if "quarantined" in output.lower():
                quarantined = True
                break
            time.sleep(1)
        if not quarantined:
            raise AssertionError("Restored hauling job was not quarantined")
        r.must_pass(SOURCE)
        r.must_pass(EMPTY_DEST)
        # Cargo may remain in NBT: do not silently delete it during quarantine.
        r.must_pass(CARGO)
        # Ensure that attempting to resume is denied; no item duplication.
        output = r.run(f"execute at {VILLAGER} run sable haul-resume")
        if "resumed" in output.lower():
            raise AssertionError("Quarantined job incorrectly resumed")
        time.sleep(3)
        r.must_pass(SOURCE)
        r.must_pass(EMPTY_DEST)
        print("PASS: restored cargo quarantined, inventories unchanged, resume rejected")

if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    elif sys.argv[1:] == ["verify"]:
        verify()
    else:
        raise SystemExit("Usage: rcon_restart_smoke.py prepare|verify")
