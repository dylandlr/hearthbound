#!/usr/bin/env python3
"""Transport-free end-to-end exercise of the real Forge haul polling contract."""
from haul_smoke_diagnostics import (
    poll_delivery,read_only_commands,acceptance_timeout_seconds,
    POLL_COUNT,POLL_INTERVAL_SECONDS,CHECKPOINT_POLL_INDICES)

TRANSFER_QUERY='execute if data block 7 100 1 Items[{id:"minecraft:wheat",Count:1b}]'

def scenario(success_index=None, bad_acceptance_id=False, bad_checkpoint_id=False,
             missing_checkpoint_response=False):
    queries=[]
    sleeps=[]
    logs=[]
    transfer_polls=0
    def send(request_id,command):
        nonlocal transfer_polls
        queries.append((request_id,command))
        if command==TRANSFER_QUERY:
            i=transfer_polls
            transfer_polls+=1
            reply_id=request_id+1 if bad_acceptance_id else request_id
            return reply_id,("Test passed, count: 1" if i==success_index
                             else "Test failed")
        if missing_checkpoint_response and command==read_only_commands()[0][1]:
            raise OSError("injected diagnostic RCON timeout")
        if bad_checkpoint_id:
            return request_id+1,"observed"
        return request_id,"observed"
    def sleep(seconds):
        sleeps.append(seconds)
    def emit(message):
        logs.append(message)
    def run():
        return poll_delivery(send,sleep,emit)
    return run,queries,sleeps,logs

def failure(call):
    try:call()
    except AssertionError:return
    raise AssertionError("fail-closed RCON error was accepted")

def main():
    immediate,commands,sleeps,logs=scenario(success_index=0)
    result=immediate()
    assert result==(True,1),result
    assert commands==[(100,TRANSFER_QUERY)]
    assert sleeps==[POLL_INTERVAL_SECONDS]
    assert any("HAUL_ACCEPTANCE_TRANSFER_POLL index=0" in x for x in logs)
    delayed,commands,sleeps,logs=scenario(success_index=38)
    assert delayed()==(True,39)
    assert len(sleeps)==39
    assert sum(command==TRANSFER_QUERY for _,command in commands)==39
    checkpoints=[x for x in logs if x.startswith("HAUL_PROGRESS_CHECKPOINT")]
    assert len(checkpoints)==8 # 30s and 60s, four read-only queries each
    assert all(any("label="+label in x for x in checkpoints)
               for label,_ in read_only_commands())
    stalled,commands,sleeps,logs=scenario(success_index=None)
    assert stalled()==(False,POLL_COUNT)
    assert len(sleeps)==75
    assert sum(sleeps)==acceptance_timeout_seconds()==150
    assert sum(command==TRANSFER_QUERY for _,command in commands)==75
    checkpoints=[x for x in logs if x.startswith("HAUL_PROGRESS_CHECKPOINT")]
    assert len(checkpoints)==len(CHECKPOINT_POLL_INDICES)*4
    assert [int(x.split("poll=")[1].split()[0])
            for x in checkpoints[::4]]==[15,30,45,60]
    assert all(
        command==TRANSFER_QUERY or command in dict(read_only_commands()).values()
        for _,command in commands)
    assert not any("HAUL_ACCEPTANCE_TRANSFER" in x for x in logs)
    malformed,*_=scenario(success_index=0,bad_acceptance_id=True)
    failure(malformed)
    malformed,*_=scenario(success_index=None,bad_checkpoint_id=True)
    failure(malformed)
    degraded,commands,sleeps,logs=scenario(
        success_index=None,missing_checkpoint_response=True)
    assert degraded()==(False,75)
    assert sum("read_error=OSError" in x for x in logs)==4
    assert not any("HAUL_ACCEPTANCE_TRANSFER" in x for x in logs)
    print("FORGE_HAUL_POLL_FAKE_RCON_E2E_PASS instant delayed stalled corrupt_ids diagnostic_timeouts")

if __name__=="__main__":
    main()
