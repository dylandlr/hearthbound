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

def poll_delivery(command, sleep, emit):
    """Check real physical chest transfer, with read-only progress snapshots.

    command(request_id, command_text) -> (response_id, response_text).
    Caller owns the authenticated RCON transport; no world-changing commands
    are allowed here. Returns (transferred, poll_count). A response-ID
    mismatch is a hard test failure, not an implicit success or skip.
    """
    for i in range(POLL_COUNT):
        sleep(POLL_INTERVAL_SECONDS)
        request_id=100+i
        got_id, output=command(
            request_id,
            'execute if data block 7 100 1 Items[{id:"minecraft:wheat",Count:1b}]')
        if got_id!=request_id:
            raise AssertionError(
                f"HAUL_ACCEPTANCE_RESPONSE_MISMATCH expected={request_id} received={got_id}")
        if "test passed" in output.lower():
            emit(f"HAUL_ACCEPTANCE_TRANSFER_POLL index={i} "
                 f"nominal_elapsed_seconds={(i+1)*POLL_INTERVAL_SECONDS}")
            return True,i+1
        if checkpoint_due(i):
            for diagnostic_index,(label,query) in enumerate(read_only_commands()):
                rid=checkpoint_request_id(i,diagnostic_index)
                try:
                    observed_id,observed=command(rid,query)
                    if observed_id!=rid:
                        raise AssertionError(
                            f"HAUL_CHECKPOINT_REQUEST_MISMATCH expected={rid} "
                            f"received={observed_id}")
                    emit(f"HAUL_PROGRESS_CHECKPOINT poll={i+1} "
                         f"nominal_elapsed_seconds={(i+1)*POLL_INTERVAL_SECONDS} "
                         f"label={label} value={observed!r}")
                except (OSError, ConnectionError, RuntimeError, ValueError) as exc:
                    emit(f"HAUL_PROGRESS_CHECKPOINT poll={i+1} "
                         f"label={label} read_error={type(exc).__name__}:{exc}")
    return False,POLL_COUNT
