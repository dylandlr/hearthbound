#!/usr/bin/env python3
"""Asymmetric colony knowledge with delayed, lossy worker-to-worker messages.

Pure deterministic simulation. Scouts directly observe their assigned source.
Workers have NO remote observation privilege; optional messages give them
bounded hints, but only an authoritative version-checked commit can haul.
"""
import argparse
import hashlib
import heapq
import json
from dataclasses import dataclass
from pathlib import Path

from simulate_colony_perception_bus import Authority, Belief, MAX_AGE

SCHEMA="hearthbound.asymmetric-colony-knowledge.v1"
SOURCES=("north-farm","south-farm","mill-store")
MODES=("no_messages","peer_messages")
PROFILES={
    "ideal":{"delay":0,"drop_mod":0},
    "delayed":{"delay":2,"drop_mod":0},
    "lossy":{"delay":1,"drop_mod":4},
    "delayed_lossy":{"delay":3,"drop_mod":3},
}

def hash_drop(seed,tick,source,receiver,mod):
    """Fault independent of policy RNG and iteration order."""
    if not mod:return False
    key=f"{seed}|{tick}|{source}|{receiver}|peer".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8],"big")%mod==0

@dataclass(frozen=True)
class Message:
    source:str
    value:str
    version:int
    observed_tick:int
    sender:str
    receiver:str
    deliver_tick:int

class Citizen:
    def __init__(self,name,local_sources,shared_sources=()):
        self.name=name
        self.local=frozenset(local_sources)
        self.shared=frozenset(shared_sources)
        self.beliefs={}
        self.received=0
        self.rejected=0

    def take_local(self,source,authority):
        if source not in self.local:
            raise PermissionError("Cannot inspect a source outside this citizen's local view")
        belief=authority.inspect(source,self.name)
        if belief is not None:self._accept(belief,authority.tick,True)

    def _accept(self,belief,now,local):
        if (belief.observed_tick>now or belief.received_tick>now or
            belief.observed_tick<0 or belief.version<1):
            self.rejected+=1
            return False
        permitted=(self.local if local else self.shared)
        if belief.source not in permitted:
            self.rejected+=1
            return False
        current=self.beliefs.get(belief.source)
        if current and (current.version>belief.version or
                        (current.version==belief.version and
                         current.observed_tick>=belief.observed_tick)):
            self.rejected+=1
            return False
        self.beliefs[belief.source]=belief
        self.received+=1
        return True

    def take_peer(self,message,now,source_is_authorized):
        if not source_is_authorized or message.receiver!=self.name or message.deliver_tick>now:
            self.rejected+=1
            return False
        belief=Belief(message.source,message.value,message.version,
                      message.observed_tick,now,"SHARED",message.sender)
        return self._accept(belief,now,False)

    def read(self,source,now):
        belief=self.beliefs.get(source)
        if belief is None:return None
        if now-belief.observed_tick>MAX_AGE or now<belief.observed_tick:
            return None
        return belief

class PeerTransport:
    """In-process trusted origin registry; NOT a cryptographic wire protocol."""
    def __init__(self,scouts,workers,profile,seed):
        self.scouts={s.name:s for s in scouts}
        self.workers={w.name:w for w in workers}
        self.profile=profile
        self.seed=seed
        self.queue=[]
        self.serial=0
        self.sent=0
        self.dropped=0
        self.delivered=0
        self.rejected=0
        self.delays=[]

    def send(self,scout,worker,source,now):
        # Only the actual registered scout object may claim this locality.
        if self.scouts.get(scout.name) is not scout or source not in scout.local:
            raise PermissionError("Invalid witness or origin")
        if self.workers.get(worker.name) is not worker or source not in worker.shared:
            raise PermissionError("Receiver lacks a source-sharing grant")
        belief=scout.read(source,now)
        if belief is None or belief.provenance!="LOCAL":
            return False
        self.sent+=1
        if hash_drop(self.seed,now,source,worker.name,self.profile["drop_mod"]):
            self.dropped+=1
            return False
        message=Message(source,belief.value,belief.version,belief.observed_tick,
                        scout.name,worker.name,now+self.profile["delay"])
        heapq.heappush(self.queue,(message.deliver_tick,self.serial,message))
        self.serial+=1
        return True

    def flush(self,now):
        while self.queue and self.queue[0][0]<=now:
            _,_,message=heapq.heappop(self.queue)
            scout=self.scouts.get(message.sender)
            valid=(scout is not None and
                   message.source in scout.local and
                   message.receiver in self.workers and
                   message.source in self.workers[message.receiver].shared)
            worker=self.workers.get(message.receiver)
            if valid and worker.take_peer(message,now,True):
                self.delivered+=1
                self.delays.append(now-message.observed_tick)
            else:
                self.rejected+=1

def simulate(seed,mode,profile,steps=150):
    if mode not in MODES or steps<1:
        raise ValueError("Bad experiment configuration")
    authority=Authority()
    scouts=[Citizen("scout_"+str(i),(source,)) for i,source in enumerate(SOURCES)]
    workers=[Citizen("worker_"+str(i),(),SOURCES) for i in range(6)]
    bus=PeerTransport(scouts,workers,profile,seed)
    for source in SOURCES:
        authority.commit(source,"EMPTY")
    # Fixed production slots, periodically rotate the stocked source; workers
    # depend on communication, not direct reads of the hidden inventory.
    hauls=0
    denied=0
    informed_actions=0
    stale_or_missing=0
    for step in range(steps):
        authority.advance()
        if step%5==0:
            src=SOURCES[(step//5)%len(SOURCES)]
            authority.commit(src,"AVAILABLE")
        # Scouts observe only their assigned source. This is the same cost
        # across communication arms; there are no privileged worker polls.
        for scout,src in zip(scouts,SOURCES):
            scout.take_local(src,authority)
            if mode=="peer_messages":
                # Workers may receive different information due to packet
                # loss, timestamp age and transport delay.
                for worker in workers:
                    bus.send(scout,worker,src,authority.tick)
        bus.flush(authority.tick)
        for worker in workers:
            # Demand schedule independent of observations and policy RNG.
            src=SOURCES[(step+int(worker.name.rsplit("_",1)[1]))%len(SOURCES)]
            belief=worker.read(src,authority.tick)
            if belief is None:
                stale_or_missing+=1
                continue
            if belief.value!="AVAILABLE":
                continue
            informed_actions+=1
            success,_=authority.authorize_haul(src,belief.version)
            if success:hauls+=1
            else:denied+=1
        # Publishing fresh stock/consumption events isn't modeled here. Scout
        # reinspection next tick will observe resulting committed versions.
    return {
        "seed":seed,"mode":mode,"profile":profile,
        "steps":steps,"scouts":len(scouts),"workers":len(workers),
        "scout_local_inspections":authority.reads,
        "worker_remote_inspections":0,
        "messages_sent":bus.sent,"messages_delivered":bus.delivered,
        "messages_dropped":bus.dropped,"messages_rejected":bus.rejected,
        "successfully_committed_hauls":hauls,"denied_stale_hauls":denied,
        "informed_action_attempts":informed_actions,
        "unknown_or_stale_decisions":stale_or_missing,
        "mean_message_age":round(sum(bus.delays)/max(1,len(bus.delays)),5),
        "minecraft_worlds":0,
    }

def benchmark(seeds=(11,13,17,19),steps=150):
    results=[]
    for seed in seeds:
        for name,profile in PROFILES.items():
            results.append({
                "seed":seed,"profile":name,
                "no_messages":simulate(seed,"no_messages",profile,steps),
                "peer_messages":simulate(seed,"peer_messages",profile,steps),
            })
    return {
        "schema":SCHEMA,"origin":"SIMULATED_ONLY",
        "minecraft_worlds":0,"minecraft_task_dispatch_authorized":False,
        "camera_frames_captured":0,"vision_models_trained":0,
        "profiles":PROFILES,"results":results,
        "limitations":[
            "World is abstract. Zero remote reads reflects a forbidden worker read interface, not measured Forge overhead",
            "Peer message origin is checked by in-process object identity, not network signatures",
            "Scouts always inspect their own source and proactively message every worker every tick",
            "Receiver has advance knowledge of allowed remote-source identifiers but not their contents",
            "No agent learned when to communicate; message policy is scripted",
        ],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("asymmetric-knowledge.json"))
    a=p.parse_args()
    report=benchmark()
    a.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    for row in report["results"]:
        a=row["no_messages"]
        b=row["peer_messages"]
        print("ASYMMETRIC_KNOWLEDGE",row["seed"],row["profile"],
              "without="+str(a["successfully_committed_hauls"]),
              "with="+str(b["successfully_committed_hauls"]),
              "messages="+str(b["messages_delivered"]),
              "denied="+str(b["denied_stale_hauls"]))
    print("ASYMMETRIC_SIMULATION_COMPLETE minecraft_worlds=0")
if __name__=="__main__":main()
