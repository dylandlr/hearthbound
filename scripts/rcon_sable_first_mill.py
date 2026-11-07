#!/usr/bin/env python3
"""Integration: Sable physically hauls wheat from a chest into powered Create millstone.

World-backed behavioral test, not evidence that Sable autonomously discovered a
recipe. No automatic research credit or teaching occurs.
"""
import json, os, re, socket, struct, time

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
    # A previous reboot can leave a second marked actor in the fixture.
    # Never interpret a successful assignment to one Sable while polling a
    # different @e[limit=1] as a valid negative outcome.
    marked=r.run("execute if entity @e[type=minecraft:villager,name=Sable]")
    if "Test passed, count: 1" not in marked:
        raise AssertionError("First mill test requires exactly one live Sable: "+marked)
    villager="@e[type=minecraft:villager,name=Sable,limit=1]"
    r.run(f"tp {villager} 2 101 1")
    witnessed=os.environ.get("HEARTHBOUND_DIRECT_WITNESS")=="1"
    witness_selector="@e[type=minecraft:villager,tag=hb_mill_source_witness,limit=1]"
    if witnessed:
        # This is a separate physical, marked villager, not Sable and not
        # an LLM-driven collaborator. A report or proximity alone cannot
        # authorize the executor's assignment.
        spawned=r.run("""summon minecraft:villager 4 101 3 {CustomName:'{"text":"MillWitness"}',Tags:["hb_mill_source_witness"],ForgeData:{"hearthbound.citizen":1b},NoAI:1b}""")
        if "Summoned new Villager" not in spawned:
            raise AssertionError("Could not spawn independent direct observer: "+spawned)
        missing=r.run(f"execute at {villager} run sable haul-witnessed 3 101 1 7 101 1 {witness_selector}")
        if "status=DENIED reason=NO_FRESH_DIRECT_SOURCE_WITNESS" not in missing:
            raise AssertionError("Hearsay-free, unobserved witness incorrectly authorized a haul: "+missing)
        empty_preflight=r.run("sable mill-reservation 7 101 1")
        if "MILL_RESERVATION NONE" not in empty_preflight:
            raise AssertionError("Denied preflight acquired a research lease: "+empty_preflight)
        observation=r.run(f"hearthbound citizen_observe 3 101 1 {witness_selector}")
        if "status=OBSERVED" not in observation or "wheat=8" not in observation:
            raise AssertionError("Independent witness failed to observe real stock: "+observation)
        before_claim=r.run(f"execute at {villager} run sable haul-witnessed 3 101 1 7 101 1 {witness_selector}")
        for token in ("WITNESSED_HAUL_ASSIGNED", "dependency=PRE_TASK_DIRECT_SOURCE_OBSERVATION",
                      "decision_origin=OPERATOR_ASSISTED", "reward_authorized=false",
                      "learning_authorized=false"):
            if token not in before_claim:
                raise AssertionError("Verified witness did not gate executor assignment: "+before_claim)
    else:
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
    if "MILL_PROCESS VERIFIED_CALLBACK" not in receipt:
        raise AssertionError("No direct Create processing callback receipt: "+receipt)
    if "wheatBefore=1 wheatAfter=0" not in receipt or "NO_RESEARCH_CREDIT" not in receipt:
        raise AssertionError("Invalid process receipt or premature knowledge credit: "+receipt)
    if witnessed:
        witnessed_process=r.run(f"execute at {villager} run sable mill-witness-probe {job_match.group(1)}")
        for token in ("MILL_WITNESS_EVIDENCE status=VERIFIED",
                      "roles=PHYSICAL_EXECUTOR,PRE_TASK_DIRECT_SOURCE_WITNESS",
                      "witness_gated_assignment=true independent_policy_choice=false",
                      "personal_milli=0 colony_milli=0 research_milli=0",
                      "reward_authorized=false", "learning_authorized=false"):
            if token not in witnessed_process:
                raise AssertionError("Post-Create two-citizen source link was not verified: "+witnessed_process)
        # The other citizen may revise their memory; an outcome cannot
        # retroactively reuse changed observations as the same original proof.
        refreshed=r.run(f"hearthbound citizen_observe 3 101 1 {witness_selector}")
        if "status=OBSERVED" not in refreshed or "wheat=7" not in refreshed:
            raise AssertionError("Witness revision intervention failed: "+refreshed)
        now_stale=r.run(f"execute at {villager} run sable mill-witness-probe {job_match.group(1)}")
        if "status=DENIED reason=WITNESS_EVIDENCE_CHANGED_OR_WRONG_JOB" not in now_stale:
            raise AssertionError("A changed witness revision silently retained attribution: "+now_stale)
        print("REAL_FORGE_TWO_ROLE_WITNESS_PASS witness_assigned_before_process=true "
              "direct_observation_only=true replay_changed_revision_denied=true "
              "personal_rewards=0 research_rewards=0",flush=True)
    # v0.15.6: joined proof must be derived from real executor NBT,
    # the real Create callback, and an active untainted mill lease.
    proposed=r.run(f"execute at {villager} run sable mill-outcome-probe {job_match.group(1)}")
    if "MILL_OUTCOME_PROPOSAL status=PROPOSED" not in proposed:
        raise AssertionError("Verified live mill outcome not joined: "+proposed)
    for expected in ("decision_origin=ACTUAL_EXECUTOR_ASSIGNMENT", "personal_milli=500",
                     "colony_milli=0 research_milli=0", "reward_authorized=false",
                     "learning_authorized=false", "NO_RESEARCH_CREDIT"):
        if expected not in proposed:
            raise AssertionError("Wrong reward proposal or authorization boundary: "+proposed)
    observed_id=re.search(r"physical_evidence_id=(\S+)",proposed)
    if not observed_id or job_match.group(1) not in observed_id.group(1):
        raise AssertionError("Missing receipt-derived process identity: "+proposed)
    if r.run(f"execute at {villager} run sable mill-outcome-probe {job_match.group(1)}") != proposed:
        raise AssertionError("Identical real receipt produced a different proposal")
    absent=r.run(f"execute at {villager} run sable mill-outcome-probe 00000000-0000-4000-8000-000000000001")
    if "status=DENIED reason=NO_CREATE_CALLBACK" not in absent:
        raise AssertionError("Nonexistent Create callback was attributed: "+absent)
    # v0.15.8: only the operator can archive a server-verified process.
    # An ADMITTED journal state is a read-only audit result, never reward
    # authorization. Duplicate inspections must not append another frame.
    journal_before=r.run(f"execute at {villager} run sable mill-outcome-journal {job_match.group(1)}")
    for expected_journal in ("CAUSAL_EVIDENCE_JOURNAL state=ADMITTED", "revalidated=true",
                             "record_count=1", "reward_authorized=false",
                             "learning_authorized=false", "NO_RESEARCH_CREDIT"):
        if expected_journal not in journal_before:
            raise AssertionError("Could not admit physical evidence into audit journal: "+journal_before)
    repeated_journal=r.run(f"execute at {villager} run sable mill-outcome-journal {job_match.group(1)}")
    if repeated_journal != journal_before:
        raise AssertionError("Idempotent journal probe changed the reported record")
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
    foreign=r.run(f"execute positioned 12 101 1 run sable mill-outcome-probe {job_match.group(1)}")
    if "status=DENIED reason=CITIZEN_OR_JOB_MISMATCH" not in foreign:
        raise AssertionError("A different real villager could reuse the first outcome: "+foreign)
    journal_foreign=r.run(f"execute positioned 12 101 1 run sable mill-outcome-journal {job_match.group(1)}")
    if "state=DENIED reason=FOREIGN_CITIZEN" not in journal_foreign:
        raise AssertionError("Different citizen mutated original journal ownership: "+journal_foreign)
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
        expired=r.run(f"execute positioned 2 101 1 run sable mill-outcome-probe {job_match.group(1)}")
        if "status=DENIED reason=TAINTED_OR_UNHELD_RESERVATION" not in expired:
            raise AssertionError("Released Create lease retained reward proposal rights: "+expired)
        journal_revoked=r.run(f"execute positioned 2 101 1 run sable mill-outcome-journal {job_match.group(1)}")
        if "state=REVOKED" not in journal_revoked or "revalidated=false" not in journal_revoked:
            raise AssertionError("Released process remained actively admitted: "+journal_revoked)
        if r.run(f"execute positioned 2 101 1 run sable mill-outcome-journal {job_match.group(1)}") != journal_revoked:
            raise AssertionError("Terminal journal revocation was not stable")
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
        # Isolate the physical ingress challenge. Without this displacement,
        # the second legitimately assigned villager could arrive and insert
        # its own wheat while we monitor the unauthorized dropped item.
        # Preserve both live reservation and task state; no intervention
        # should be credited to the agent.
        # Keep the parked actor's chunk loaded for later adversarial test restore.
        r.run("forceload add 32 0 47 4")
        # The original test teleported the citizen outside the prepared
        # stone floor. A parked agent could fall away or die before restore.
        # This is an OPERATOR fixture intervention, not agent behavior.
        r.run("setblock 45 100 1 minecraft:stone replace")
        frozen=r.run("execute positioned 12 101 1 run data merge entity @e[type=minecraft:villager,name=Sable,sort=nearest,limit=1,distance=..4] {NoAI:1b}")
        if "Modified entity data" not in frozen:
            raise AssertionError("Could not safely freeze outsider-ingress test citizen: "+frozen)
        parked=r.run("execute positioned 12 101 1 run tp @e[type=minecraft:villager,name=Sable,sort=nearest,limit=1,distance=..4] 45 101 1")
        if "Teleported" not in parked:
            raise AssertionError("Could not isolate assigned citizen: "+parked)
        lease_parked=r.run("sable mill-reservation 7 101 1")
        if f"job={job_match.group(1)}" in lease_parked or "MILL_RESERVATION HELD" not in lease_parked:
            raise AssertionError("Citizen isolation lost the reserved mill: "+lease_parked)
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
        # An item entity can move or be picked up outside this guarded
        # machine. Entity presence is not a causal ingestion receipt. Require
        # instead that no process callback happened for this second job and
        # neither authorized input nor Create output changed.
        no_callback=r.run(f"sable mill-process {new_lease.split('job=')[1].split()[0]}")
        if "MILL_PROCESS NONE" not in no_callback:
            raise AssertionError("External wheat unexpectedly yielded a Create callback: "+no_callback)
        machine_clean=r.run("sable mill-inspect 7 101 1")
        if not re.search(r"wheat=0(\D|$)", machine_clean) or not re.search(r"flour=0(\D|$)", machine_clean):
            raise AssertionError("External item modified the reserved mill machine: "+machine_clean)
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
        # Restore the assigned villager only after the adversarial flour
        # mutation is installed. Its first pickup must encounter a tainted mill.
        restored=r.run("execute positioned 45 101 1 run tp @e[type=minecraft:villager,name=Sable,sort=nearest,limit=1,distance=..5] 12 101 1")
        if "Teleported" not in restored:
            raise AssertionError("Could not resume post-admission taint test: "+restored)
        unfrozen=r.run("execute positioned 12 101 1 run data merge entity @e[type=minecraft:villager,name=Sable,sort=nearest,limit=1,distance=..4] {NoAI:0b}")
        if "Modified entity data" not in unfrozen:
            raise AssertionError("Could not resume assigned citizen AI: "+unfrozen)
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
        # A source-independent, operator-side baseline. No in-game agent may
        # read this file; after reboot the complete receipt must match exactly.
        if "status=PROPOSED" not in proposed:
            raise AssertionError("No valid mill outcome to use for restart comparison")
        with open("mill-outcome-pre-restart.json", "w", encoding="utf-8") as out:
            json.dump({"schema": "hearthbound.outcome-restart-checkpoint.v1",
                       "job": job_match.group(1), "receipt": proposed,
                       "journal": journal_before},
                      out, sort_keys=True, indent=2)
        with open("mill-evidence-job.txt", "w", encoding="utf-8") as out:
            out.write(job_match.group(1) + "\n")
        r.run("save-all flush")
        print("Saved journal for restart verification", flush=True)
        r.run("stop")
    print("PASS: Sable physically hauled wheat into powered Create millstone, flour observed, no false discovery credit",flush=True)
