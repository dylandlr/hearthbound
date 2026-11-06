#!/usr/bin/env python3
"""Read-only diagnostics for the real Forge Sable wheat-haul smoke fixture.

The acceptance condition remains a physical source-to-destination transfer,
not an audit response. Sampling never issues movement, inventory edits or
reconciliation commands.
"""
POLL_INTERVAL_SECONDS = 2
POLL_COUNT = 75
CHECKPOINT_POLL_INDICES = (14, 29, 44, 59)
SOURCE_POS = (3, 100, 1)
DESTINATION_POS = (7, 100, 1)
_ALLOWED = (
    ("job", 'execute at @e[type=minecraft:villager,name=Sable,limit=1] run sable haul-audit'),
    ("citizen", 'data get entity @e[type=minecraft:villager,name=Sable,limit=1] Pos'),
    ("source", 'data get block 3 100 1 Items'),
    ("destination", 'data get block 7 100 1 Items'),
)

def read_only_commands():
    return _ALLOWED

def checkpoint_due(index):
    if type(index) is not int or index < 0 or index >= POLL_COUNT:
        raise ValueError("invalid real Forge poll index")
    return index in CHECKPOINT_POLL_INDICES

def checkpoint_request_id(poll_index, command_index):
    if (not checkpoint_due(poll_index) or type(command_index) is not int
        or command_index < 0 or command_index >= len(_ALLOWED)):
        raise ValueError("invalid checkpoint diagnostic request")
    return 800 + poll_index * len(_ALLOWED) + command_index

def acceptance_timeout_seconds():
    return POLL_COUNT * POLL_INTERVAL_SECONDS
