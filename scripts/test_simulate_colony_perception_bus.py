#!/usr/bin/env python3
"""Deterministic event and belief safety contracts; no Minecraft sensor claims."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("simulate_colony_perception_bus.py")
s=importlib.util.spec_from_file_location("colony_perception",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def main():
    a=m.Authority()
    farm=a.commit("farm-chest","AVAILABLE")
    alice=m.Knowledge("alice",("farm-chest",),allow_share=True)
    bob=m.Knowledge("bob",("farm-chest",),allow_share=True)
    outsider=m.Knowledge("outsider",(),allow_share=True)
    bus=m.Bus()
    bus.subscribe("farm-chest",alice)
    bus.subscribe("farm-chest",bob)
    try:bus.subscribe("farm-chest",outsider)
    except PermissionError:pass
    else:raise AssertionError("Unauthorized subscription accepted")
    bus.publish(farm,a.tick)
    assert bus.delivered==2
    assert alice.read("farm-chest",0)["value"]=="AVAILABLE"
    assert bob.read("farm-chest",0)["version"]==1
    assert outsider.read("farm-chest",0)["status"]=="UNKNOWN"
    # A server task is an atomic, version-checked consumption, never the
    # cache itself granting authority to retrieve inventory.
    ok,empty=a.authorize_haul("farm-chest",1)
    assert ok and empty.version==2
    assert a.authorize_haul("farm-chest",1)==(False,None)
    bus.publish(empty,a.tick)
    assert alice.read("farm-chest",0)["value"]=="EMPTY"
    assert not alice.event(farm,a.tick)  # old event must not roll back cache
    assert alice.read("farm-chest",0)["version"]==2
    # Forged citizen event must be rejected by the (simulated) trusted bus.
    forged=m.Event("INVENTORY_CHANGED","farm-chest",99,0,"AVAILABLE","intruder")
    try:bus.publish(forged,0)
    except PermissionError:pass
    else:raise AssertionError("Spoofed bus event was accepted")
    assert not alice.event(forged,0)
    # Shared information can be distributed, but source scope and age matter.
    copied=alice.share("farm-chest",0)
    assert copied is not None and copied.provenance=="SHARED"
    assert not bob.observe(copied,0) # same revision is not an update
    newcomer=m.Knowledge("new",("farm-chest",),allow_share=True)
    assert newcomer.observe(copied,0)
    assert newcomer.read("farm-chest",0)["value"]=="EMPTY"
    limited=m.Knowledge("limited",("farm-chest",),allow_share=False)
    assert not limited.observe(copied,0)
    for _ in range(m.MAX_AGE+1):a.advance()
    assert newcomer.read("farm-chest",a.tick)["status"]=="STALE"
    assert newcomer.share("farm-chest",a.tick) is None
    assert newcomer.read("farm-chest",a.tick)["value"] is None
    # Vision may suggest a state, never provide a trusted inventory fact.
    image=m.Belief("farm-chest","AVAILABLE",100,a.tick,a.tick,
                   "VISUAL_HYPOTHESIS","camera")
    assert newcomer.observe(image,a.tick)
    assert newcomer.read("farm-chest",a.tick)["status"]=="UNVERIFIED_VISUAL"
    assert newcomer.share("farm-chest",a.tick) is None
    assert a.authorize_haul("farm-chest",100)==(False,None)
    # Unknown source observations must not crash the cache or leak facts.
    assert limited.read("unknown-chest",a.tick)["status"]=="UNKNOWN"
    # Untrusted future timestamps must be rejected.
    future=m.Belief("farm-chest","AVAILABLE",101,a.tick+1,a.tick+1,"LOCAL","alice")
    assert not newcomer.observe(future,a.tick)
    # Polling and events should generate distinct, reproducible load.
    result=m.benchmark(seeds=(11,13),steps=45,citizens=6)
    assert result==m.benchmark(seeds=(11,13),steps=45,citizens=6)
    assert result["minecraft_worlds"]==0
    assert result["minecraft_action_authorized"] is False
    assert result["image_model_trained"] is False
    for row in result["rows"]:
        poll=row["poll_every_tick"]
        subs=row["event_subscriptions"]
        shared=row["event_plus_shared"]
        assert poll["authoritative_inspections"]==45*6*3
        assert subs["authoritative_inspections"]==0
        assert shared["authoritative_inspections"]==0
        assert poll["denied_hauls"]>=0 and subs["denied_hauls"]>=0
        assert subs["bus_messages"]>0
    print("PASS permission boundaries, event order, TTL, shared beliefs, visual quarantine, authoritative hauls and deterministic baseline")

if __name__=="__main__":main()
