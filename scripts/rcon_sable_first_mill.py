#!/usr/bin/env python3
"""Integration: Sable physically hauls wheat from a chest into powered Create millstone.

World-backed behavioral test, not evidence that Sable autonomously discovered a
recipe. Verified Create callbacks now grant research credit, and a nearby citizen can be taught only after the teacher actually knows the recipe.
"""
import os, re, socket, struct, time

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
    # Unavailable resource/machine must not generate research hypotheses.
    r.contains(f"execute as {villager} at @s run sable experiment-local 3 101 1 2 101 1",
               "EXPERIMENT DEFER")
    r.contains(f"execute as {villager} at @s run sable experiment-local 3 101 1 7 101 1",
               "EXPERIMENT PROPOSED")
    r.contains(f"execute as {villager} at @s run sable hypothesis-mill-inspect",
               "HYPOTHESIS PROPOSED")

    r.contains(f"execute at {villager} run sable haul 3 101 1 7 101 1","Sable assigned wheat haul")
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

    # Knowledge must spread through an explicit local social action rather than a global unlock.
    r.contains(f"execute as {villager} at @s run sable spawn-named Iven","Hearthbound citizen spawned: Iven")
    teaching=r.run(f'execute as {villager} at @s run sable teach-nearest "create:milling/wheat"')
    if "TEACHING_SUCCESS" not in teaching or "teacher=Sable" not in teaching or "student=Iven" not in teaching:
        raise AssertionError("Verified recipe could not be taught locally: "+teaching)
    student_knowledge=r.run('execute as @e[type=minecraft:villager,name=Iven,limit=1] at @s run sable tech-inspect')
    if "create:milling/wheat" not in student_knowledge or "source=TAUGHT" not in student_knowledge:
        raise AssertionError("Iven did not retain socially transmitted milling knowledge: "+student_knowledge)
    # Opt-in policy-driven social transmission; no teach-nearest command.
    r.contains(f"execute as {villager} at @s run sable spawn-named Moss",
               "Hearthbound citizen spawned: Moss")
    request=r.run('execute as @e[type=minecraft:villager,name=Moss,limit=1] at @s run sable learning-request "create:milling/wheat"')
    if "LEARNING_REQUEST recipe=create:milling/wheat" not in request:
        raise AssertionError("Moss did not persist a local request: "+request)
    r.contains(f"execute as {villager} at @s run sable auto-teach-on",
               "Autonomous social teaching enabled")
    learned=False
    for _ in range(12):
        time.sleep(1)
        moss=r.run('execute as @e[type=minecraft:villager,name=Moss,limit=1] at @s run sable tech-inspect')
        if "create:milling/wheat" in moss and "source=TAUGHT" in moss:
            learned=True
            break
    if not learned:
        raise AssertionError("Policy-controlled nearby teaching did not transfer milling knowledge")
    cleared=r.run('execute as @e[type=minecraft:villager,name=Moss,limit=1] at @s run sable learning-request-inspect')
    if "LEARNING_REQUEST NONE" not in cleared:
        raise AssertionError("Learning request survived successful teaching: "+cleared)
    # A third student independently requests and receives the observed technology.
    r.contains(f"execute as {villager} at @s run sable spawn-named Nia",
               "Hearthbound citizen spawned: Nia")
    nia='@e[type=minecraft:villager,name=Nia,limit=1]'
    r.contains(f"execute as {nia} at @s run sable auto-learn-on",
               "Autonomous learning enabled")
    nia_learned=False
    for _ in range(25):
        time.sleep(1)
        nia_knowledge=r.run(f"execute as {nia} at @s run sable tech-inspect")
        if "create:milling/wheat" in nia_knowledge and "source=TAUGHT" in nia_knowledge:
            nia_learned=True
            break
    if not nia_learned:
        raise AssertionError("Nia did not autonomously request and learn milling")
    r.contains(f"execute as {nia} at @s run sable learning-request-inspect",
               "LEARNING_REQUEST NONE")
    r.contains(f"execute as {villager} at @s run sable auto-teach-off",
               "Autonomous social teaching disabled")
    # A completed job may NOT be released while flour remains in the machine.
    occupied_release=r.run(f"execute at {villager} run sable mill-release 7 101 1 {job_match.group(1)}")
    if "Collect all millstone output" not in occupied_release:
        raise AssertionError("Occupied millstone was released without clearing output: "+occupied_release)
    still_reserved=r.run("sable mill-reservation 7 101 1")
    if f"job={job_match.group(1)}" not in still_reserved:
        raise AssertionError("Failed release destroyed original reservation: "+still_reserved)
    # Adversarial test: another Hearthbound citizen must not claim the same
    # millstone even after Sable finished delivering her item.
    r.run('setblock 10 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:8b}]} replace')
    r.contains("execute positioned 12 101 1 run sable spawn", "Sable spawned")
    collision=r.run("execute positioned 12 101 1 run sable haul 10 101 1 7 101 1")
    if "millstone reserved" not in collision.lower():
        raise AssertionError("Second citizen assigned conflicting mill haul: "+collision)
    reservation_after=r.run("sable mill-reservation 7 101 1")
    if f"job={job_match.group(1)}" not in reservation_after:
        raise AssertionError("Rejected assignment stole first reservation: "+reservation_after)
    # A different mill reservation may be cancelled before wheat is picked
    # up. The original machine's completed experimental hold must survive.
    r.run("setblock 11 101 2 create:millstone replace")
    r.contains("execute positioned 12 101 1 run sable haul 10 101 1 11 101 2",
               "Sable assigned wheat haul")
    r.contains("execute positioned 12 101 1 run sable haul-cancel", "Unpicked haul cancelled")
    released=r.run("sable mill-reservation 11 101 2")
    if "MILL_RESERVATION NONE" not in released:
        raise AssertionError("Cancelled pre-pickup mill job still holds reservation: "+released)
    still_owned=r.run("sable mill-reservation 7 101 1")
    if f"job={job_match.group(1)}" not in still_owned:
        raise AssertionError("Cancelling other job released the original mill: "+still_owned)
    if os.environ.get("HEARTHBOUND_RESTART_PROBE") != "1":
        # This is an admin-driven test-fixture reset, NOT physical collection.
        # In real play an item transport mechanism must remove the flour.
        r.run("data modify block 7 101 1 OutputInventory.Items set value []")
        cleared=r.run("sable mill-inspect 7 101 1")
        if not re.search(r"flour=0(\D|$)", cleared):
            raise AssertionError("Output not cleared before audited release: "+cleared)
        # A job UUID mismatch must never release another citizen's lease.
        mismatch=r.run("execute positioned 2 101 1 run sable mill-release 7 101 1 00000000-0000-4000-8000-000000000001")
        if "does not match" not in mismatch:
            raise AssertionError("Wrong job ID was not rejected: "+mismatch)
        released_ok=r.run(f"execute positioned 2 101 1 run sable mill-release 7 101 1 {job_match.group(1)}")
        if "Mill reservation released with audit tombstone" not in released_ok:
            raise AssertionError("Validated completed mill was not released: "+released_ok)
        after_release=r.run("sable mill-reservation 7 101 1")
        if "MILL_RESERVATION NONE" not in after_release:
            raise AssertionError("Released mill still occupied: "+after_release)
        replay=r.run(f"execute positioned 2 101 1 run sable mill-release 7 101 1 {job_match.group(1)}")
        if "does not match" not in replay:
            raise AssertionError("Duplicate release was not rejected: "+replay)
        # Negative control: external flour left in a released machine must
        # make a new research lease fail. Do not treat that flour as Sable's.
        r.run('data modify block 7 101 1 OutputInventory.Items set value [{Slot:0,id:"create:wheat_flour",Count:1b}]')
        preexisting=r.run("sable mill-inspect 7 101 1")
        if not re.search(r"flour=[1-9]\d*", preexisting):
            raise AssertionError("Could not seed pre-existing flour negative control: "+preexisting)
        contaminated=r.run("execute positioned 12 101 1 run sable haul 10 101 1 7 101 1")
        if "millstone reserved" not in contaminated.lower():
            raise AssertionError("New job accepted contaminated millstone: "+contaminated)
        if "MILL_RESERVATION NONE" not in r.run("sable mill-reservation 7 101 1"):
            raise AssertionError("Contaminated machine acquired reservation unexpectedly")
        r.run("data modify block 7 101 1 OutputInventory.Items set value []")
        # Second citizen can now acquire the cleaned mill with a fresh job ID.
        reassigned=r.run("execute positioned 12 101 1 run sable haul 10 101 1 7 101 1")
        if "Sable assigned wheat haul" not in reassigned:
            raise AssertionError("New citizen cannot reuse audited released mill: "+reassigned)
        new_lease=r.run("sable mill-reservation 7 101 1")
        if "MILL_RESERVATION HELD" not in new_lease or f"job={job_match.group(1)}" in new_lease:
            raise AssertionError("New job does not own reused mill: "+new_lease)
        # Real Forge capability route must deny insertion from an outside actor
        # without a Sable authorization scope. This must not contaminate inputs.
        # Positive control: same direct-belt API must still insert wheat into
        # an UNRESERVED Create millstone (no fake denial due to broken fixture).
        r.run("setblock 11 101 0 create:millstone replace")
        open_belt=r.run("sable mill-probe-open-belt 11 101 0")
        if "OPEN_BELT ACCEPTED" not in open_belt:
            raise AssertionError("Open Create millstone incorrectly blocked belt insertion: "+open_belt)
        open_input=r.run("sable mill-inspect 11 101 0")
        if not re.search(r"wheat=1(\D|$)",open_input):
            raise AssertionError("Open belt insertion did not deposit wheat: "+open_input)
        # Physical item-entity ingress: this is the same real-world route
        # used by the standalone powered mill experiment, not a direct API
        # invocation. The reserved, powered mill must not swallow outsider wheat.
        r.run('summon minecraft:item 7.5 102.15 1.5 {Item:{id:"minecraft:wheat",Count:1b},PickupDelay:32767s,Tags:["hearthbound_external_probe"]}')
        for _ in range(6):
            time.sleep(.5)
            probe_state=r.run("sable mill-inspect 7 101 1")
            if not re.search(r"wheat=0(\D|$)",probe_state):
                raise AssertionError("Dropped outsider wheat entered reserved mill: "+probe_state)
        remaining_entity=r.run("execute positioned 7 101 1 if entity @e[type=minecraft:item,tag=hearthbound_external_probe,distance=..5] run say external-wheat-preserved")
        if "external-wheat-preserved" not in remaining_entity:
            raise AssertionError("Physical outsider wheat was consumed or disappeared: "+remaining_entity)
        r.run("kill @e[type=minecraft:item,tag=hearthbound_external_probe]")
        belt_denied=r.run("sable mill-probe-belt-insert 7 101 1")
        if "BELT_INSERT DENIED" not in belt_denied:
            raise AssertionError("Reserved mill accepted unauthorized Create direct belt transfer: "+belt_denied)
        denied=r.run("sable mill-probe-external-insert 7 101 1")
        if "EXTERNAL_INSERT DENIED" not in denied:
            raise AssertionError("Reserved mill accepted unsanctioned Forge insert: "+denied)
        state=r.run("sable mill-inspect 7 101 1")
        if not re.search(r"wheat=0(\D|$)",state):
            raise AssertionError("Outside insertion modified reserved input: "+state)

        # Inject flour AFTER this second reservation, but BEFORE Sable's
        # pickup. Hearthbound must permanently taint this job, not extract wheat.
        second_job=re.search(r"job=([0-9a-fA-F-]{36})",new_lease)
        if not second_job:
            raise AssertionError("Fresh mill lease has no job UUID: "+new_lease)
        r.run('data modify block 7 101 1 OutputInventory.Items set value [{Slot:0,id:"create:wheat_flour",Count:1b}]')
        tainted=False
        for _ in range(12):
            time.sleep(1)
            status2=r.run("execute positioned 12 101 1 run sable haul-status")
            lease2=r.run("sable mill-reservation 7 101 1")
            if "MILL_RESERVATION TAINTED" in lease2 and "tainted" in status2.lower():
                tainted=True
                break
        if not tainted:
            raise AssertionError("Post-admission flour mutation did not taint experiment: "+lease2+" "+status2)
        evidence2=r.run(f"sable mill-process {second_job.group(1)}")
        if "MILL_PROCESS INVALIDATED" not in evidence2 or "NO_RESEARCH_CREDIT" not in evidence2:
            raise AssertionError("Tainted second experiment retained usable processing evidence: "+evidence2)
        # Cleaning the inventory must not remove the persistent taint marker.
        r.run("data modify block 7 101 1 OutputInventory.Items set value []")
        persisted_taint=r.run("sable mill-reservation 7 101 1")
        if "MILL_RESERVATION TAINTED" not in persisted_taint:
            raise AssertionError("Cleaning physical output silently healed taint: "+persisted_taint)

    if os.environ.get("HEARTHBOUND_RESTART_PROBE") != "1":
        # Post-delivery substitution experiment on a separate unpowered Create
        # mill. Removing the motor ensures Create cannot process before the
        # adversarial insertion. All changes are done by the server test fixture.
        r.run('setblock 10 101 3 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:8b}]} replace')
        r.run("setblock 11 100 3 minecraft:stone replace")
        r.run("setblock 11 101 3 create:millstone replace")
        r.contains("execute positioned 12 101 3 run sable spawn", "Sable spawned")
        r.contains("execute positioned 12 101 3 run sable haul 10 101 3 11 101 3",
                   "Sable assigned wheat haul")
        third_job=None
        for _ in range(150):
            time.sleep(1)
            result=r.run("sable mill-reservation 11 101 3")
            found=re.search(r"job=([0-9a-fA-F-]{36})",result)
            if found: third_job=found.group(1)
            delivered=r.run("execute positioned 12 101 3 run sable haul-status")
            if "Haul complete" in delivered: break
            if "quarantined" in delivered.lower() or "paused" in delivered.lower():
                raise AssertionError("Third citizen failed to deliver wheat: "+delivered)
        else:
            raise AssertionError("Third citizen did not deliver into stopped Create mill")
        if not third_job: raise AssertionError("Third job reservation missing")
        # External actor adds identical wheat after the authorized insertion.
        r.run('data modify block 11 101 3 InputInventory.Items set value [{Slot:0,id:"minecraft:wheat",Count:2b}]')
        added=r.run("data get block 11 101 3 InputInventory")
        if "Count: 2" not in added and "Count:2" not in added:
            raise AssertionError("Failed to introduce extra wheat: "+added)
        # Processing is deliberately still unpowered. Per-tick surveillance
        # must taint this reservation before Create gets any chance to mill it.
        pre_power_tainted=False
        for _ in range(8):
            time.sleep(.5)
            pre_power=r.run("sable mill-reservation 11 101 3")
            if "MILL_RESERVATION TAINTED" in pre_power:
                pre_power_tainted=True
                break
        if not pre_power_tainted:
            raise AssertionError("Per-tick monitor missed extra wheat while motor was stopped: "+pre_power)
        r.run("setblock 11 100 3 create:creative_motor[facing=up] replace")
        callback_seen=False
        for _ in range(100):
            time.sleep(.75)
            audit=r.run("sable mill-reservation 11 101 3")
            if "MILL_RESERVATION TAINTED" in audit:
                callback_seen=True
                break
        if not callback_seen:
            raise AssertionError("Create processing with extra wheat did not taint job")
        blocked=r.run(f"sable mill-process {third_job}")
        if "MILL_PROCESS INVALIDATED" not in blocked or "NO_RESEARCH_CREDIT" not in blocked:
            raise AssertionError("Extra-input processing was accepted: "+blocked)
        # The HEAD veto should preserve both wheat items for inspection.
        inventory=r.run("data get block 11 101 3 InputInventory")
        if "Count: 2" not in inventory and "Count:2" not in inventory:
            raise AssertionError("Unauthorized Create processing consumed tampered input: "+inventory)
        print("PASS: extra wheat inserted after authorized delivery invalidated processing evidence",flush=True)
    if os.environ.get("HEARTHBOUND_RESTART_PROBE") == "1":
        with open("mill-evidence-job.txt", "w", encoding="utf-8") as out:
            out.write(job_match.group(1) + "\n")
        r.run("save-all flush")
        print("Saved journal for restart verification", flush=True)
        r.run("stop")
    print("PASS: verified Create milling granted causal research knowledge and Sable taught Iven locally",flush=True)
