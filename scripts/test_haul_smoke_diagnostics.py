#!/usr/bin/env python3
"""Check real Forge hauling diagnostics cannot mask delivery failures."""
import ast
from pathlib import Path
from haul_smoke_diagnostics import (
    POLL_COUNT,POLL_INTERVAL_SECONDS,CHECKPOINT_POLL_INDICES,
    checkpoint_due,checkpoint_request_id,read_only_commands,
    acceptance_timeout_seconds)

def rejected(fn):
    try:fn()
    except ValueError:return
    raise AssertionError("accepted illegal poll index")

def main():
    assert POLL_COUNT==75
    assert POLL_INTERVAL_SECONDS==2
    assert acceptance_timeout_seconds()==150
    assert CHECKPOINT_POLL_INDICES==(14,29,44,59)
    assert [i+1 for i in range(POLL_COUNT) if checkpoint_due(i)]==[15,30,45,60]
    assert len(read_only_commands())==4
    assert len({checkpoint_request_id(i,j)
                for i in CHECKPOINT_POLL_INDICES
                for j in range(4)})==16
    assert all(checkpoint_request_id(i,j)>703
               for i in CHECKPOINT_POLL_INDICES for j in range(4))
    rejected(lambda:checkpoint_due(-1))
    rejected(lambda:checkpoint_due(75))
    rejected(lambda:checkpoint_request_id(0,0))
    rejected(lambda:checkpoint_request_id(14,5))
    allowed_prefixes=("data get ", "execute at ")
    for label,command in read_only_commands():
        assert command.startswith(allowed_prefixes),(label,command)
        if command.startswith("execute at "):
            assert command.endswith(" run sable haul-audit"),command
        assert not any(token in command for token in (
            " tp "," setblock "," fill "," summon "," haul 3 ",
            " item replace "," data modify "," gamemode "," kill "))
    script=Path(__file__).with_name("rcon_smoke.py").read_text()
    ast.parse(script)
    assert 'for i in range(POLL_COUNT):' in script
    assert 'if checkpoint_due(i):' in script
    assert 'if not transferred:' in script
    assert 'raise AssertionError("Sable did not deliver wheat within 150 seconds")' in script
    assert 'execute if data block 7 100 1 Items[{id:"minecraft:wheat",Count:1b}]' in script
    print("FORGE_READ_ONLY_HAUL_TIMELINE_CHECKPOINTS_PASS")

if __name__=="__main__":
    main()
