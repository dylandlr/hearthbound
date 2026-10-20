#!/usr/bin/env python3
"""Disposable in-world colony fixture for human-control camera capture.

Keeps this UI demonstration separate from the autonomous science experiment.
All entities are tagged and removed before the subsequent scenario.
"""
import os
import socket
import struct


def packet(request_id, kind, command):
    body = struct.pack("<ii", request_id, kind) + command.encode() + b"\0\0"
    return struct.pack("<i", len(body)) + body


def recv(sock):
    def exact(n):
        result = b""
        while len(result) < n:
            part = sock.recv(n - len(result))
            if not part:
                raise ConnectionError("RCON closed")
            result += part
        return result
    count = struct.unpack("<i", exact(4))[0]
    if not 10 <= count <= 1000000:
        raise ValueError("Invalid RCON length")
    body = exact(count)
    return struct.unpack("<i", body[:4])[0], body[8:-2].decode(errors="replace")


def main():
    with socket.create_connection(("127.0.0.1", 25575), timeout=20) as sock:
        sock.settimeout(20)
        sock.sendall(packet(1, 3, os.environ["HEARTHBOUND_RCON_PASSWORD"]))
        request_id, _ = recv(sock)
        if request_id != 1:
            request_id, _ = recv(sock)
        if request_id != 1:
            raise RuntimeError("RCON login rejected")

        def cmd(command):
            nonlocal request_id
            request_id += 1
            sock.sendall(packet(request_id, 2, command))
            reply_id, response = recv(sock)
            if reply_id != request_id:
                raise RuntimeError("RCON mismatched response")
            print(f"FIXTURE {command} => {response}", flush=True)
            if any(message in response.lower() for message in
                   ("unknown command", "incorrect argument", "unknown or incomplete command")):
                raise RuntimeError("Fixture command failed: " + command)
            return response

        cmd("gamerule doMobSpawning false")
        cmd("forceload add 0 0")
        # Build an enclosed, intentionally simple roofed room at a known Y.
        cmd("fill 1 100 1 11 105 11 minecraft:air")
        cmd("fill 1 100 1 11 100 11 minecraft:spruce_planks")
        for wall in (
            "fill 1 101 1 11 104 1 minecraft:stone_bricks",
            "fill 1 101 11 11 104 11 minecraft:stone_bricks",
            "fill 1 101 1 1 104 11 minecraft:stone_bricks",
            "fill 11 101 1 11 104 11 minecraft:stone_bricks",
            "fill 1 105 1 11 105 11 minecraft:spruce_planks",
        ):
            cmd(wall)
        cmd("fill 4 105 4 8 105 8 minecraft:air")
        cmd("setblock 5 101 5 minecraft:crafting_table")
        cmd("setblock 8 101 5 minecraft:barrel")
        cmd("setblock 3 101 5 create:millstone")
        for name, x, z in (("Sable", 4, 6), ("Rowan", 6, 6), ("Iris", 8, 6)):
            nbt = '{CustomName:\'{"text":"' + name + '"}\',Tags:["hb_camera_fixture"],NoAI:1b,PersistenceRequired:1b}'
            cmd(f"summon minecraft:villager {x} 101 {z} {nbt}")
        cmd("tp HBCamera 6 101 6")
        cmd("gamemode spectator HBCamera")
        cmd("effect give HBCamera minecraft:night_vision 600 0 true")
        cmd("time set noon")
        print("PLAYER_CAMERA_FIXTURE_READY", flush=True)


if __name__ == "__main__":
    main()
