#!/usr/bin/env python3
"""Experimental, permissioned event-driven colony perception (no Minecraft control).

World commits are authoritative; agents receive bounded, partially observable
messages. Shared beliefs are NOT authority to dispatch resource-consuming tasks.
The simulation and counts in this file are synthetic, not Forge measurements.
"""
import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

SCHEMA="hearthbound.colony-perception-event.v1"
KINDS=("INVENTORY_CHANGED","MACHINE_CHANGED","JOB_COMPLETED")
SOURCE_TYPES=("LOCAL","SHARED","VISUAL_HYPOTHESIS")
MAX_AGE=6

@dataclass(frozen=True)
class Event:
    kind: str
    source: str
    version: int
    tick: int
    value: str
    actor: str

    def __post_init__(self):
        if self.kind not in KINDS or not self.source or not self.actor:
            raise ValueError("Unrecognized event")
        if type(self.version) is not int or self.version<1 or type(self.tick) is not int or self.tick<0:
            raise ValueError("Invalid event version or tick")
        if self.value not in ("EMPTY","AVAILABLE","POWERED","UNPOWERED","COMPLETE"):
            raise ValueError("Unrecognized sensor value")

@dataclass(frozen=True)
class Belief:
    source: str
    value: str
    version: int
    observed_tick: int
    received_tick: int
    provenance: str
    observer: str

    def fresh(self,now):
        return 0<=now-self.observed_tick<=MAX_AGE

class Authority:
    """The hidden world state and atomically committed source versions."""
    def __init__(self):
        self.values={}
        self.versions={}
        self.tick=0
        self.reads=0

    def advance(self):
        self.tick+=1

    def commit(self,source,value,kind="INVENTORY_CHANGED",actor="server"):
        version=self.versions.get(source,0)+1
        event=Event(kind,source,version,self.tick,value,actor)
        self.values[source]=value
        self.versions[source]=version
        return event

    def inspect(self,source,agent):
        self.reads+=1
        if source not in self.values: return None
        return Belief(source,self.values[source],self.versions[source],
                      self.tick,self.tick,"LOCAL",agent)

    def authorize_haul(self,source,expected_version):
        """Consume exactly one available supply at an authoritative revision.

        Never use the recipient's cached belief alone to decide. This models a
        single-source atomic task commit, not Minecraft transaction semantics.
        """
        if (type(expected_version) is not int or
            self.versions.get(source)!=expected_version or
            self.values.get(source)!="AVAILABLE"):
            return False,None
        event=self.commit(source,"EMPTY")
        return True,event

class Knowledge:
    def __init__(self,agent,visible_sources,allow_share=False):
        self.agent=agent
        self.visible_sources=frozenset(visible_sources)
        self.allow_share=allow_share
        self.entries={}
        self.rejected=0
        self.accepted=0

    def observe(self,belief,now):
        if belief.source not in self.visible_sources:
            self.rejected+=1;return False
        if belief.provenance not in SOURCE_TYPES or belief.observed_tick>now or belief.received_tick>now:
            self.rejected+=1;return False
        if belief.provenance=="SHARED" and not self.allow_share:
            self.rejected+=1;return False
        if belief.version<1 or belief.observed_tick<0 or belief.received_tick<belief.observed_tick:
            self.rejected+=1;return False
        old=self.entries.get(belief.source)
        if old and (belief.version<old.version or
                    (belief.version==old.version and belief.observed_tick<=old.observed_tick)):
            self.rejected+=1;return False
        self.entries[belief.source]=belief
        self.accepted+=1
        return True

    def event(self,event,now,provenance="LOCAL"):
        if event.tick>now:
            self.rejected+=1;return False
        b=Belief(event.source,event.value,event.version,event.tick,now,provenance,event.actor)
        return self.observe(b,now)

    def read(self,source,now):
        b=self.entries.get(source)
        if b is None:return {"status":"UNKNOWN","value":None,"version":None}
        if not b.fresh(now):
            return {"status":"STALE","value":None,"version":b.version}
        if b.provenance=="VISUAL_HYPOTHESIS":
            return {"status":"UNVERIFIED_VISUAL","value":None,"version":b.version}
        return {"status":"KNOWN","value":b.value,"version":b.version}

    def share(self,source,now):
        b=self.entries.get(source)
        if not self.allow_share or not b or not b.fresh(now) or b.provenance=="VISUAL_HYPOTHESIS":
            return None
        return Belief(b.source,b.value,b.version,b.observed_tick,now,"SHARED",self.agent)

class Bus:
    """Only subscribed, permitted agents receive authoritative event notices."""
    def __init__(self):
        self.subscribers={}
        self.published=0
        self.delivered=0

    def subscribe(self,source,knowledge):
        if source not in knowledge.visible_sources:
            raise PermissionError("Subscription outside citizen visibility")
        self.subscribers.setdefault(source,[])
        if knowledge not in self.subscribers[source]:
            self.subscribers[source].append(knowledge)

    def publish(self,event,now):
        self.published+=1
        for receiver in self.subscribers.get(event.source,()):
            if receiver.event(event,now):
                self.delivered+=1

def simulate(seed,mode,steps=140,citizens=12):
    if mode not in ("poll_every_tick","event_subscriptions","event_plus_shared"):
        raise ValueError("Unknown comparison mode")
    if steps<1 or citizens<2:
        raise ValueError("Invalid experiment dimensions")
    rng=random.Random(seed)
    authority=Authority()
    bus=Bus()
    sources=("mill-chest","farm-chest","smelter-chest")
    citizens_by_name=[Knowledge("citizen_"+str(i),sources,
                                allow_share=mode=="event_plus_shared")
                      for i in range(citizens)]
    for source in sources:
        event=authority.commit(source,"EMPTY")
        if mode!="poll_every_tick":
            for k in citizens_by_name:bus.subscribe(source,k)
            bus.publish(event,authority.tick)
    delivered_messages=0
    successful_hauls=0
    denied_hauls=0
    stale_beliefs=0
    for t in range(steps):
        authority.advance()
        # Sparse changes are server-owned. Citizens cannot see hidden stock.
        if t%9==0:
            src=sources[(t//9)%len(sources)]
            event=authority.commit(src,"AVAILABLE")
            if mode!="poll_every_tick":bus.publish(event,authority.tick)
        if mode=="poll_every_tick":
            for k in citizens_by_name:
                for src in sources:
                    b=authority.inspect(src,k.agent)
                    k.observe(b,authority.tick)
        elif mode=="event_plus_shared" and t%13==0:
            # One citizen may send a bounded, verified fact; version/ACL
            # checks still govern receiving citizen belief caches.
            sender=citizens_by_name[(t//13)%citizens]
            receiver=citizens_by_name[((t//13)+1)%citizens]
            src=sources[(t//13)%len(sources)]
            shared=sender.share(src,authority.tick)
            if shared is not None and receiver.observe(shared,authority.tick):
                delivered_messages+=1

        worker=citizens_by_name[rng.randrange(citizens)]
        src=sources[rng.randrange(len(sources))]
        view=worker.read(src,authority.tick)
        if view["status"]=="STALE":stale_beliefs+=1
        if view["status"]=="KNOWN" and view["value"]=="AVAILABLE":
            ok,event=authority.authorize_haul(src,view["version"])
            if ok:
                successful_hauls+=1
                if mode!="poll_every_tick":bus.publish(event,authority.tick)
            else:
                denied_hauls+=1
                # A failed real action means the cached belief is not enough;
                # no invented inventory recovery or bypass occurs here.
    return {"seed":seed,"mode":mode,"world_steps":steps,
            "citizens":citizens,"sources":len(sources),
            "authoritative_inspections":authority.reads,
            "bus_messages":bus.delivered,"citizen_shares":delivered_messages,
            "successful_hauls":successful_hauls,
            "denied_hauls":denied_hauls,
            "stale_belief_reads":stale_beliefs,
            "minecraft_worlds":0}

def benchmark(seeds=(11,13,17,19),steps=140,citizens=12):
    rows=[]
    for seed in seeds:
        rows.append({name:simulate(seed,name,steps,citizens) for name in
                     ("poll_every_tick","event_subscriptions","event_plus_shared")})
    return {"schema":"hearthbound.colony-perception-benchmark.v1",
            "event_schema":SCHEMA,"origin":"SIMULATED_ONLY",
            "minecraft_worlds":0,"minecraft_action_authorized":False,
            "image_model_trained":False,
            "comparison":"synthetic repeated inspections versus permissioned subscriptions",
            "rows":rows,
            "limitations":[
                "Inventory reads and event delivery are abstract counters, not measured server CPU time",
                "Event bus delivery is instantaneous and reliable in this prototype",
                "Network effects, Minecraft chunks, AI rendering and actual Create block events are unimplemented",
                "Shared memory is an observation channel, never task execution authority",
            ]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("colony-perception-events.json"))
    a=p.parse_args()
    r=benchmark()
    a.output.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    for row in r["rows"]:
        for name,trial in row.items():
            print("PERCEPTION_SIM",trial["seed"],name,
                  "inspections="+str(trial["authoritative_inspections"]),
                  "deliveries="+str(trial["bus_messages"]),
                  "hauls="+str(trial["successful_hauls"]),
                  "denied="+str(trial["denied_hauls"]))
    print("PERCEPTION_SIM_COMPLETE minecraft_worlds=0")
if __name__=="__main__":main()
