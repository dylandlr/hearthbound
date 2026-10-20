#!/usr/bin/env python3
"""Autonomous research acceptance: citizen chooses and hauls into powered Create millstone.

World-backed behavioral test, not evidence that Sable autonomously discovered a
recipe. Verified Create callbacks now grant research credit, and a nearby citizen can be taught only after the teacher actually knows the recipe.
"""
import os, re, socket, struct, time, json, pathlib

def packet(req, typ, value):
    body=struct.pack("<ii",req,typ)+value.encode()+b"\0\0"
    return struct.pack("<i",len(body))+body

class Rcon:
    def __enter__(self):
        self.s=socket.create_connection(("127.0.0.1",25575),timeout=20)
        self.s.settimeout(20)
        self.seq=10
        self.s.sendall(packet(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
        req,_=self.recv()
        if req!=1: req,_=self.recv()
        if req!=1: raise RuntimeError("Bad RCON authentication")
        return self
    def __exit__(self,*_): self.s.close()
    def recv(self):
        def exact(n):
            b=b""
            while len(b)<n:
                chunk=self.s.recv(n-len(b))
                if not chunk: raise ConnectionError("RCON disconnected")
                b+=chunk
            return b
        n=struct.unpack("<i",exact(4))[0]
        if n<10 or n>1000000: raise ValueError("Bad RCON response size")
        data=exact(n)
        return struct.unpack("<i",data[:4])[0],data[8:-2].decode(errors="replace")
    def run(self,cmd):
        self.seq+=1
        self.s.sendall(packet(self.seq,2,cmd))
        req,out=self.recv()
        if req!=self.seq: raise AssertionError(f"Wrong RCON ID: {req}")
        print(f"{cmd} => {out}",flush=True)
        return out
    def contains(self,cmd,want):
        output=self.run(cmd)
        if want.lower() not in output.lower(): raise AssertionError(f"{cmd}: expected {want}, got {output}")
        return output

with Rcon() as r:
    for cmd in (
        "gamerule doMobSpawning false",
        "forceload add 0 0",
        "fill 0 99 0 12 105 4 minecraft:air",
        "fill 0 100 0 12 100 4 minecraft:stone",
        'setblock 3 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:8b}]} replace',
        "setblock 7 100 1 create:creative_motor[facing=up] replace",
        "setblock 7 101 1 create:millstone replace",
    ): r.run(cmd)
    # Visual-only workshop dressing. Keep the documented wheat source, mill,
    # citizen route, and actual Create machine physics unchanged.
    # The fixture still clears the world first, so build scenery afterwards.
    for cmd in (
        "fill 0 100 5 12 100 10 minecraft:spruce_planks",
        "fill 0 100 0 12 100 4 minecraft:spruce_planks",
        "fill 0 101 10 12 104 10 minecraft:stone_bricks",
        "fill 0 101 0 12 104 0 minecraft:stone_bricks",
        "fill 0 101 0 0 104 10 minecraft:stone_bricks",
        "fill 12 101 0 12 104 10 minecraft:stone_bricks",
        "fill 1 102 0 4 103 0 minecraft:glass_pane",
        "fill 8 102 0 11 103 0 minecraft:glass_pane",
        "fill 1 102 10 4 103 10 minecraft:glass_pane",
        "fill 8 102 10 11 103 10 minecraft:glass_pane",
        "fill 0 105 0 12 105 10 minecraft:spruce_slab",
        "fill 4 105 3 8 105 8 minecraft:air",
        "setblock 5 101 9 minecraft:crafting_table",
        "setblock 9 101 9 minecraft:barrel",
        "setblock 1 101 9 minecraft:lantern",
        "setblock 11 101 9 minecraft:lantern",
        "setblock 10 101 6 minecraft:oak_fence",
        "setblock 7 100 1 create:creative_motor[facing=up] replace",
        "setblock 7 101 1 create:millstone replace",
    ): r.run(cmd)
    speed=0.
    for _ in range(40):
        obs=r.run("data get block 7 101 1 Speed")
        m=re.search(r"data: (-?\d+(?:\.\d+)?)f",obs)
        if m:
            speed=float(m.group(1))
            if abs(speed)>0: break
        time.sleep(.5)
    if speed==0: raise AssertionError("Create millstone not powered")
    r.contains("sable spawn","Sable spawned")
    villager="@e[type=minecraft:villager,name=Sable,limit=1]"
    r.run(f"tp {villager} 2 101 1")
    # The agent has no hand-issued haul or proposal: both are selected at tick time.
    r.contains(f"execute as {villager} at @s run sable auto-research-on",
               "AUTO_RESEARCH ENABLED")
    def game_tick():
        value=r.run("time query gametime")
        m=re.search(r"(\d+)\s*$",value)
        if not m: raise AssertionError("No Minecraft game tick: "+value)
        return int(m.group(1))
    started=time.monotonic()
    start_tick=game_tick()
    metrics={"schema_version":1,"scenario":"autonomous-scientist","starting_wheat":8,"millstone_powered":True}
    assigned=False
    for _ in range(60):
        time.sleep(1)
        trace=r.run(f"execute as {villager} at @s run sable haul-status")
        hypothesis=r.run(f"execute as {villager} at @s run sable hypothesis-mill-inspect")
        if "HYPOTHESIS PROPOSED" in hypothesis and (
                "Walking to source" in trace or "Walking to destination" in trace
                or "Haul complete" in trace):
            assigned=True
            break
    if not assigned:
        raise AssertionError("Citizen never independently proposed and assigned experiment")
    metrics["seconds_to_proposal"]=round(time.monotonic()-started,3)
    metrics["ticks_to_proposal"]=game_tick()-start_tick

    # Only Sable is allowed to transport the wheat; no /summon item.
    complete=False
    for _ in range(180):
        time.sleep(1)
        status=r.run(f"execute at {villager} run sable haul-status")
        if "Haul complete" in status:
            complete=True
            break
        if "quarantined" in status.lower() or "paused" in status.lower():
            audit=r.run(f"execute at {villager} run sable haul-audit")
            raise AssertionError("Haul stopped: "+audit)
    if not complete: raise AssertionError("Sable did not deliver wheat to Create millstone")
    metrics["seconds_to_haul"]=round(time.monotonic()-started,3)
    metrics["ticks_to_haul"]=game_tick()-start_tick
    r.contains('execute if data block 3 101 1 Items[{id:"minecraft:wheat",Count:7b}]',"Test passed")
    produced=False
    for _ in range(100):
        time.sleep(.75)
        observation=r.run("sable mill-inspect 7 101 1")
        match=re.search(r"flour=(\d+)",observation)
        if match and int(match.group(1))>0:
            produced=True
            if "NO_RESEARCH_CREDIT" not in observation:
                raise AssertionError("Unverified science credit")
            break
    if not produced: raise AssertionError("Sable delivered wheat but Create produced no flour")
    metrics["seconds_to_first_flour"]=round(time.monotonic()-started,3)
    metrics["ticks_to_first_flour"]=game_tick()-start_tick
    metrics["wheat_consumed"]=1
    # Machine output can become visible before the citizen’s 20-tick sample.
    # Wait for the ordered trace rather than failing on that benign race.
    trace=""
    for _ in range(15):
        trace=r.run(f"execute at {villager} run sable mill-trace")
        if "phase=CYCLE_OUTPUT_OBSERVED" in trace:
            break
        time.sleep(1)
    # The server sampled the *running Create machine* before its output.
    timing=re.search(r"processingTick=(\d+) outputTick=(\d+)",trace)
    if not timing or int(timing.group(1))<=0 or int(timing.group(2))<=int(timing.group(1)):
        raise AssertionError("No ordered powered-cycle observations: "+trace)
    authorized=re.search(r"authorizedTick=(\d+) authorizedInput=(\d+)",trace)
    if not authorized or int(authorized.group(1))<=0 or int(authorized.group(2))!=1:
        raise AssertionError("No exact authorized wheat insertion evidence: "+trace)
    if "verdict=CANDIDATE_WHEAT_TO_FLOUR" not in trace:
        raise AssertionError("Physical delivery trace did not link to observed output: "+trace)
    if "NO_RESEARCH_CREDIT" not in trace or "phase=CYCLE_OUTPUT_OBSERVED" not in trace:
        raise AssertionError("Trace improperly attributed confirmed recipe knowledge: "+trace)
    job_match=re.search(r"job=([0-9a-fA-F-]{36})",trace)
    if not job_match:
        raise AssertionError("No job identity in machine trace: "+trace)
    persisted=r.run(f"sable mill-evidence {job_match.group(1)}")
    if "MILL_EVIDENCE CANDIDATE" not in persisted or "NO_RESEARCH_CREDIT" not in persisted:
        raise AssertionError("Candidate milling evidence not persisted: "+persisted)
    if f"job={job_match.group(1)}" not in persisted:
        raise AssertionError("World journal evidence not associated with Sable job: "+persisted)
    reservation=r.run("sable mill-reservation 7 101 1")
    if "MILL_RESERVATION HELD" not in reservation or f"job={job_match.group(1)}" not in reservation:
        raise AssertionError("Sable millstone reservation absent or mismatched: "+reservation)
    receipt=r.run(f"sable mill-process {job_match.group(1)}")
    r.contains(f"execute as {villager} at @s run sable hypothesis-mill-inspect",
               "HYPOTHESIS CONFIRMED")
    if "MILL_PROCESS VERIFIED_CALLBACK" not in receipt:
        raise AssertionError("No direct Create processing callback receipt: "+receipt)
    if "wheatBefore=1 wheatAfter=0" not in receipt or "RESEARCH_CREDIT_GRANTED" not in receipt:
        raise AssertionError("Verified Create receipt did not grant research credit: "+receipt)
    reward=r.run(f"sable mill-reward {job_match.group(1)}")
    if "RESEARCH_REWARD VERIFIED" not in reward or "research=" not in reward:
        raise AssertionError("Verified Create process has no persisted research reward: "+reward)
    teacher_knowledge=r.run(f"execute as {villager} at @s run sable tech-inspect")
    if "create:milling/wheat" not in teacher_knowledge or "source=DIRECT_EXPERIMENT" not in teacher_knowledge:
        raise AssertionError("Sable did not learn wheat milling from physical evidence: "+teacher_knowledge)

    r.contains(f"execute as {villager} at @s run sable hypothesis-mill-inspect",
               "HYPOTHESIS CONFIRMED")
    r.contains(f"execute as {villager} at @s run sable auto-research-off",
               "AUTO_RESEARCH DISABLED")
    metrics["seconds_to_confirmation"]=round(time.monotonic()-started,3)
    metrics["ticks_to_confirmation"]=game_tick()-start_tick
    metrics["confirmed"]=True
    out=pathlib.Path(os.environ.get("HEARTHBOUND_SCENARIO_METRICS","simulation-results/metrics.json"))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(metrics,indent=2)+"\\n")
    print("AUTONOMOUS FIRST MILL PASS: proposal, haul, Create receipt, research credit, knowledge")
