#!/usr/bin/env python3
"""Synthetic perception safety and asymmetric-information tests."""
import importlib.util
from pathlib import Path

p=Path(__file__).with_name("simulate_asymmetric_colony_knowledge.py")
spec=importlib.util.spec_from_file_location("asymmetric_knowledge",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def main():
    world=m.Authority()
    world.commit("north-farm","AVAILABLE")
    scout=m.Citizen("scout_0",("north-farm",))
    worker=m.Citizen("worker_0",(),("north-farm",))
    outsider=m.Citizen("outsider",(),())
    scout.take_local("north-farm",world)
    for c in (worker,outsider):
        try:c.take_local("north-farm",world)
        except PermissionError:pass
        else:raise AssertionError("Worker accessed forbidden inventory")
    bus=m.PeerTransport([scout],[worker],{"delay":2,"drop_mod":0},11)
    assert bus.send(scout,worker,"north-farm",0)
    assert not worker.read("north-farm",0)
    bus.flush(1)
    assert not worker.read("north-farm",1)
    bus.flush(2)
    b=worker.read("north-farm",2)
    assert b is not None and b.provenance=="SHARED" and b.version==1
    assert bus.delivered==1
    # Receiver cannot accept old revision over a newer one.
    world.advance()
    changed=world.commit("north-farm","EMPTY")
    scout.take_local("north-farm",world)
    assert bus.send(scout,worker,"north-farm",world.tick)
    bus.flush(world.tick+2)
    assert worker.read("north-farm",3).value=="EMPTY"
    late=m.Message("north-farm","AVAILABLE",1,0,"scout_0","worker_0",3)
    assert not worker.take_peer(late,3,True)
    assert worker.read("north-farm",3).value=="EMPTY"
    # Stale belief cannot authorize a haul; server revision must match.
    assert world.authorize_haul("north-farm",1)==(False,None)
    for _ in range(m.MAX_AGE+1):world.advance()
    assert worker.read("north-farm",world.tick) is None
    # Unauthorized sender or receiver source is rejected by transport.
    fake=m.Citizen("scout_0",("north-farm",))
    try:bus.send(fake,worker,"north-farm",world.tick)
    except PermissionError:pass
    else:raise AssertionError("Forged scout object permitted")
    try:bus.send(scout,outsider,"north-farm",world.tick)
    except PermissionError:pass
    else:raise AssertionError("Undeclared receiver permitted")
    # Two policies get matched source production and scout inspection rates.
    report=m.benchmark(seeds=(11,13),steps=50)
    assert report==m.benchmark(seeds=(11,13),steps=50)
    assert report["minecraft_worlds"]==0
    assert report["minecraft_task_dispatch_authorized"] is False
    assert report["camera_frames_captured"]==0
    assert len(report["results"])==8
    for row in report["results"]:
        none=row["no_messages"]
        shared=row["peer_messages"]
        assert none["scout_local_inspections"]==shared["scout_local_inspections"]==50*3
        assert none["worker_remote_inspections"]==shared["worker_remote_inspections"]==0
        assert none["successfully_committed_hauls"]==0
        assert shared["messages_sent"]>0
        assert shared["successfully_committed_hauls"]>=0
        assert shared["denied_stale_hauls"]>=0
    assert any(row["peer_messages"]["successfully_committed_hauls"]>0
               for row in report["results"])
    print("PASS asymmetric views, delayed delivery, loss, version rejection, ACLs, preflight and deterministic simulated evidence")
if __name__=="__main__":main()
