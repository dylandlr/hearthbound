#!/usr/bin/env python3
"""Real Forge integration test for Sable insertion failures on disposable CI world."""
import os
import socket
import struct
import time

PASSWORD = os.environ["HEARTHBOUND_RCON_PASSWORD"]
VILLAGER = '@e[type=minecraft:villager,name=Sable,limit=1,sort=nearest]'

class Rcon:
    def __enter__(self):
        self.sock = socket.create_connection(("127.0.0.1", 25575), timeout=20)
        self.sock.settimeout(20)
        self.seq = 10
        self.sock.sendall(self.pkt(1, 3, PASSWORD))
        rid, _ = self.recv()
        if rid != 1:
            rid, _ = self.recv()
        if rid != 1:
            raise RuntimeError("RCON authorization failed")
        return self

    def __exit__(self, *_):
        self.sock.close()

    @staticmethod
    def pkt(rid, kind, data):
        payload = struct.pack("<ii", rid, kind) + data.encode() + b"\0\0"
        return struct.pack("<i", len(payload)) + payload

    def recv(self):
        def exact(n):
            buf = b""
            while len(buf) < n:
                part = self.sock.recv(n - len(buf))
                if not part:
                    raise ConnectionError("RCON closed")
                buf += part
            return buf
        size = struct.unpack("<i", exact(4))[0]
        if not 10 <= size <= 100000:
            raise ValueError("Invalid RCON packet length")
        data = exact(size)
        return struct.unpack("<i", data[:4])[0], data[8:-2].decode(errors="replace")

    def cmd(self, command):
        self.seq += 1
        self.sock.sendall(self.pkt(self.seq, 2, command))
        rid, output = self.recv()
        if rid != self.seq:
            raise AssertionError(f"Wrong RCON response {rid} for {command}")
        print(f"{command}: {output}", flush=True)
        return output

    def check(self, command):
        out = self.cmd(command)
        if "test passed" not in out.lower():
            raise AssertionError(f"Failed assertion: {command}: {out}")

    def expect(self, command, phrase):
        out = self.cmd(command)
        if phrase.lower() not in out.lower():
            raise AssertionError(f"Unexpected response: {command}: {out}")

def scenario(r, mode, source_x):
    # Use a fresh disposable Sable each scenario.
    r.cmd(f"kill {VILLAGER}")
    r.expect("sable spawn", "Sable spawned")
    r.cmd(f"tp {VILLAGER} 2 100 1")
    r.expect(f"execute at {VILLAGER} run sable haul {source_x} 100 1 7 100 1",
             "Sable assigned wheat haul")
    r.expect(f"execute at {VILLAGER} run sable fault-insert-{mode}",
             "Injection armed")
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        # The command must run from the villager's position, otherwise
        # nearestSable on a command block/RCON console may find no entity.
        out = r.cmd(f"execute at {VILLAGER} run sable haul-status")
        if "quarantined" in out.lower():
            break
        time.sleep(1)
    else:
        raise AssertionError(f"No quarantine after injected {mode} fault")
    r.check(f'execute if data block {source_x} 100 1 Items[{{id:"minecraft:wheat",Count:7b}}]')
    if mode == "before":
        r.check('execute unless data block 7 100 1 Items[{id:"minecraft:wheat"}]')
    else:
        r.check('execute if data block 7 100 1 Items[{id:"minecraft:wheat",Count:1b}]')
    r.check(f'execute if data entity {VILLAGER} ForgeData."hearthbound.haul".cargo')
    # Even with a real quarantined job, closure must fail while Sable retains
    # cargo. The job ID comes from Minecraft's actual persistent NBT.
    # The read-only audit provides the job UUID in a command-safe format.
    audit = r.cmd(f"execute at {VILLAGER} run sable haul-audit")
    import re
    match = re.search(r"job=([0-9a-fA-F-]{36})", audit)
    if not match:
        raise AssertionError("Missing UUID in haul audit: " + audit)
    close_out = r.cmd(f"execute at {VILLAGER} run sable haul-reconcile-close {match.group(1)}")
    if "closed" in close_out.lower():
        raise AssertionError("Cargo-bearing quarantined job was incorrectly closed")
    if "cargo still held" not in close_out.lower():
        raise AssertionError("Closure did not reject cargo-bearing job: " + close_out)
    denied = r.cmd(f"execute at {VILLAGER} run sable haul-resume")
    if "resumed" in denied.lower():
        raise AssertionError("Quarantined haul was resumed")
    time.sleep(3)
    if mode == "before":
        r.check('execute unless data block 7 100 1 Items[{id:"minecraft:wheat"}]')
    else:
        r.check('execute if data block 7 100 1 Items[{id:"minecraft:wheat",Count:1b}]')
    print(f"PASS {mode}: quarantined, observed inventory effect, no re-insertion",flush=True)

with Rcon() as r:
    r.cmd("gamerule doMobSpawning false")
    for cmd in [
        "forceload add 0 0 10 4",
        "fill 0 99 0 10 99 4 minecraft:stone",
        "fill 0 100 0 10 103 4 minecraft:air",
    ]:
        r.cmd(cmd)
    for mode, source_x in (("before", 3), ("after", 4)):
        r.cmd(f'setblock {source_x} 100 1 minecraft:chest{{Items:[{{Slot:0b,id:"minecraft:wheat",Count:8b}}]}} replace')
        r.cmd("setblock 7 100 1 minecraft:chest replace")
        scenario(r, mode, source_x)
print("Real Minecraft insertion-fault regressions passed")
