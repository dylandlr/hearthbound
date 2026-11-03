#!/usr/bin/env python3
"""Standalone checks for Minecraft RCON packet parsing, without opening a server."""
import ast
from pathlib import Path
import socket
import struct

module = ast.parse(Path(__file__).with_name("rcon_smoke.py").read_text())
nodes = [n for n in module.body if isinstance(n, ast.FunctionDef) and
         n.name in ("packet","recv_exact","response")]
scope = {"socket":socket, "struct":struct}
exec(compile(ast.Module(body=nodes,type_ignores=[]),"<rcon-functions>","exec"),scope)
packet = scope["packet"]
response = scope["response"]

class FakeSocket:
    def __init__(self, data):
        self.data = data
    def recv(self, amount):
        head, self.data = self.data[:amount], self.data[amount:]
        return head

def check():
    # A stale empty Minecraft RESPONSE_VALUE can appear before next command.
    stream = packet(21, 0, "") + packet(22, 0, "Sable assigned wheat haul.")
    got = response(FakeSocket(stream))
    assert got[0] == 22 and "assigned wheat" in got[2]
    # Authentication can legitimately return an empty payload.
    got = response(FakeSocket(packet(1, 2, "")), allow_empty=True)
    assert got[0] == 1 and got[2] == ""
    # Empty-only streams must fail, never masquerade as successful Minecraft output.
    try:
        response(FakeSocket(packet(2, 0, "")))
        raise AssertionError("empty command response incorrectly accepted")
    except ConnectionError:
        pass
    print("PASS: delayed empty RCON frame, empty auth, empty command rejection")

if __name__=="__main__":
    check()
