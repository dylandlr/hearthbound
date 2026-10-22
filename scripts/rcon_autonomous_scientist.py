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
        print(f"HB_EVENT_TIME monotonic_ns={time.monotonic_ns()} command={cmd}",flush=True)
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
    if not produced:
        # This is evidence collection only: never inject items, grant research
        # credit, or relabel an incomplete Create process as success.
        diagnostics = {}
        for label, command in (
            ("haul_audit", f"execute as {villager} at @s run sable haul-audit"),
            ("mill_trace", f"execute at {villager} run sable mill-trace"),
            ("mill_reservation", "sable mill-reservation 7 101 1"),
            ("block_nbt", "data get block 7 101 1"),
            ("nearby_items", "execute positioned 7 101 1 run data get entity @e[type=minecraft:item,distance=..4,limit=1,sort=nearest]"),
        ):
            try:
                diagnostics[label] = r.run(command)
            except Exception as exc:
                diagnostics[label] = f"DIAGNOSTIC_ERROR {exc}"
        pathlib.Path("gameplay-capture").mkdir(exist_ok=True)
        pathlib.Path("gameplay-capture/mill-failure-diagnostics.json").write_text(
            json.dumps(diagnostics, indent=2) + "\\n")
        raise AssertionError("Sable delivered wheat but Create produced no verified flour; "
                             "see mill-failure-diagnostics.json")
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
    out.write_text(json.dumps(metrics,indent=2)+"\n")
    print("AUTONOMOUS FIRST MILL PASS: proposal, haul, Create receipt, research credit, knowledge")
    # Independent citizen identities and individual priors are tested separately
    # from Sable's proven autonomous milling policy. They are not yet job-trained.
    residents = {}
    for name, x, z in (("Sable", 2, 1), ("Rowan", 4, 7), ("Iris", 8, 7)):
        if name != "Sable":
            r.contains(f"execute positioned {x} 101 {z} run sable spawn-named {name}",
                       "Hearthbound citizen spawned: " + name)
        selector=f"@e[type=minecraft:villager,name={name},limit=1]"
        entity_data=r.run(f"data get entity {selector} UUID")
        if "[I;" not in entity_data:
            raise AssertionError("No distinct citizen UUID for "+name+": "+entity_data)
        profile=r.run(f"execute as {selector} at @s run sable instinct-inspect")
        if "INSTINCT" not in profile or "starting priors only" not in profile:
            raise AssertionError("Missing persistent individual instinct profile for "+name+": "+profile)
        residents[name]={"entity_uuid_evidence":entity_data[:180],"instinct_profile":profile}
    if len(set(v["entity_uuid_evidence"] for v in residents.values())) != 3:
        raise AssertionError("Citizens do not have three unique UUIDs")
    population_out=pathlib.Path("gameplay-capture/citizen-baseline.json")
    population_out.parent.mkdir(parents=True,exist_ok=True)
    population_out.write_text(json.dumps({
        "schema_version":1,
        "scope":"individual identity and instinct baseline; not independent jobs",
        "residents":residents
    },indent=2)+"\n")
    print("THREE CITIZEN BASELINE PASS: distinct entities, inspectable instinct priors")

    # Rowan's haul is chosen by his OWN tick policy, not /sable haul.
    # Separate source/destination prevent interference with Sable's mill job.
    r.run('setblock 3 101 7 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:4b}]} replace')
    r.run("setblock 9 101 7 minecraft:chest replace")
    rowan="@e[type=minecraft:villager,name=Rowan,limit=1]"
    r.contains(f"execute as {rowan} at @s run sable auto-work-discover 3 101 7 9 101 7",
               "Configured discover-library auto work")
    r.contains(f"execute as {rowan} at @s run sable auto-work-on","Auto work enabled")
    rowan_trace=""
    rowan_assigned=False
    rowan_completed=False
    for _ in range(140):
        time.sleep(1)
        rowan_trace=r.run(f"execute as {rowan} at @s run sable auto-work-status")
        status=r.run(f"execute as {rowan} at @s run sable haul-status")
        if "haulIssued=true" in rowan_trace:
            rowan_assigned=True
        if not rowan_trace.strip() or not status.strip():
            diagnostic=r.run("data get entity "+rowan+" Pos")
            nearby=r.run("execute positioned 6 101 7 run execute if entity @e[type=minecraft:villager,name=Rowan,distance=..32] ")
            raise AssertionError("Rowan disappeared or command was unaddressable: position="+diagnostic+" nearby="+nearby+" last="+rowan_trace)
        if rowan_assigned and "Haul complete" in status:
            rowan_completed=True
            break
    if not rowan_assigned or not rowan_completed:
        raise AssertionError("Rowan did not autonomously select and complete a haul: "+rowan_trace)
    source_evidence=r.run("data get block 3 101 7 Items")
    # Source began with four wheat. A legitimate one-unit delivery must
    # leave exactly three, regardless of which inventory slot contains it.
    if "minecraft:wheat" not in source_evidence or not re.search(r"Count:[ ]*3b",source_evidence):
        raise AssertionError("Rowan did not debit exactly one source wheat: "+source_evidence)
    destination_evidence=r.run("data get block 9 101 7 Items")
    if "minecraft:wheat" not in destination_evidence:
        raise AssertionError("Rowan completion lacked destination wheat evidence: "+destination_evidence)
    r.contains(f"execute as {rowan} at @s run sable auto-work-off","Auto work disabled")
    residents["Rowan"]["independent_haul"]={
        "auto_assigned":True,"completed":True,"source_evidence":source_evidence[:350],
        "destination_evidence":destination_evidence[:350]}
    population_out.write_text(json.dumps({
        "schema_version":2,"scope":"individual identities plus Rowan tick-selected physical haul",
        "residents":residents
    },indent=2)+"\n")
    print("ROWAN AUTONOMOUS HAUL PASS: independently selected and physically completed")

    # Separate contention acceptance: two citizens attempt the SAME source.
    # Assignment is deliberately admin-driven here to isolate the source-lock
    # invariant; this is NOT evidence of autonomous shared-job selection.
    source_pos="4 101 8"
    dest_pos="9 101 8"
    r.run('setblock 4 101 8 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:2b}]} replace')
    r.run("setblock 9 101 8 minecraft:chest replace")
    iris="@e[type=minecraft:villager,name=Iris,limit=1]"
    r.contains(f"execute as {iris} at @s run sable haul {source_pos} {dest_pos}",
               "assigned wheat haul")
    owner_before=r.run(f"hearthboundclaims owner {source_pos}")
    if "belongs to" not in owner_before:
        raise AssertionError("No persisted source claim after Iris assignment: "+owner_before)
    r.run("scoreboard objectives add hb_claim_test dummy")
    r.run(f"execute store result score #second hb_claim_test run execute as {villager} at @s run sable haul {source_pos} {dest_pos}")
    denied=r.run("scoreboard players get #second hb_claim_test")
    if not re.search(r"\b0\s*\[hb_claim_test\]", denied):
        raise AssertionError("Second citizen was not denied the claimed source: "+denied)
    owner_after=r.run(f"hearthboundclaims owner {source_pos}")
    if owner_before != owner_after:
        raise AssertionError("Contending citizen changed claim owner")
    finished=False
    for _ in range(100):
        time.sleep(1)
        status=r.run(f"execute as {iris} at @s run sable haul-status")
        if "Haul complete" in status:
            finished=True
            break
    if not finished:
        raise AssertionError("Claim winner did not finish: "+status)
    freed=r.run(f"hearthboundclaims owner {source_pos}")
    if "No source claim" not in freed:
        raise AssertionError("Completed work leaked source claim: "+freed)
    remaining=r.run(f"data get block {source_pos} Items")
    delivered=r.run(f"data get block {dest_pos} Items")
    if "Count: 1b" not in remaining or "minecraft:wheat" not in delivered:
        raise AssertionError("Claim test did not conserve inventory: "+remaining+" "+delivered)
    contention={
        "schema_version":1,"test":"shared_source_claim",
        "mode":"operator-triggered isolation test; not autonomous task selection",
        "first_owner": "Iris","second_contender":"Sable",
        "loser_denied":True,"claim_released":True,
        "claim_owner_before":owner_before,"claim_owner_after_rejection":owner_after,
        "rejected_command_score":denied,"claim_after_completion":freed,
        "source_after":remaining,"destination_after":delivered
    }
    pathlib.Path("gameplay-capture/contention-evidence.json").write_text(
        json.dumps(contention,indent=2)+"\n")
    print("SHARED RESOURCE CONTENTION PASS: second claimant denied, ownership preserved, claim released")

    # Two autonomous tick policies now observe the same explicitly authorized
    # source. Their destinations differ so successful work remains attributable.
    # This tests exclusive assignment, not alternative-job selection.
    shared_source="3 101 7"
    # Use a standalone barrel to avoid double-chest inventory merging with
    # the previously used Rowan fixture. Assert the mutation itself succeeded.
    r.contains('setblock 3 101 7 minecraft:barrel{Items:[{Slot:0b,id:"minecraft:wheat",Count:2b}]} replace',
               "Changed the block")
    wheat_before=r.run(f"data get block {shared_source} Items")
    if "minecraft:wheat" not in wheat_before or "Count: 2b" not in wheat_before:
        raise AssertionError("No executable wheat offer in shared source: "+wheat_before)
    r.run("setblock 9 101 8 minecraft:chest replace")
    r.run("setblock 9 101 7 minecraft:chest replace")
    for actor,destination in ((iris,"9 101 8"),(rowan,"9 101 7")):
        r.contains(f"execute as {actor} at @s run sable auto-work-discover {shared_source} {destination}",
                   "Configured discover-library auto work")
        r.contains(f"execute as {actor} at @s run sable auto-work-on","Auto work enabled")
    # Record each citizen's prior decision tick. A stale trace from the
    # earlier Rowan haul cannot count as participation in this experiment.
    def choice_tick(status):
        match=re.search(r"WORK_CHOICE tick=(\d+)",status)
        return int(match.group(1)) if match else -1
    baseline={
        name:choice_tick(r.run(f"execute as {actor} at @s run sable auto-work-status"))
        for name,actor in (("Iris",iris),("Rowan",rowan))
    }
    observations={}
    selected=None
    for _ in range(45):
        time.sleep(1)
        for name,actor in (("Iris",iris),("Rowan",rowan)):
            observations[name]=r.run(f"execute as {actor} at @s run sable auto-work-status")
            if (choice_tick(observations[name]) > baseline[name]
                    and "outcome=HAUL_ASSIGNED" in observations[name]):
                selected=name
        if selected: break
    if not selected:
        raise AssertionError("Neither autonomous citizen selected the common source: "+str(observations))
    original_claim=r.run(f"hearthboundclaims owner {shared_source}")
    if "belongs to" not in original_claim:
        raise AssertionError("No winner retained the shared source lock: "+original_claim)
    other="Iris" if selected=="Rowan" else "Rowan"
    # The other policy must have time to evaluate the same offer; it may
    # report a DECLINED haul or no executable work while the source is locked.
    for _ in range(16):
        time.sleep(1)
        observations[other]=r.run(f"execute as {iris if other=='Iris' else rowan} at @s run sable auto-work-status")
        if choice_tick(observations[other]) > baseline[other]: break
    if choice_tick(observations[other]) <= baseline[other]:
        raise AssertionError("Competing citizen never made a fresh decision: "+str(observations))
    current_claim=r.run(f"hearthboundclaims owner {shared_source}")
    # A completed delivery legitimately releases its source claim. Distinguish
    # release from ownership transfer by checking cargo and final citizen state.
    claim_released="No source claim" in current_claim
    if current_claim != original_claim and not claim_released:
        # A fresh owner can legitimately claim the source after the original
        # haul completed and released it. Validate the earlier winning job
        # before classifying this as a claim theft.
        original_actor=iris if selected=="Iris" else rowan
        original_haul=r.run(f"execute as {original_actor} at @s run sable haul-status")
        if "Haul complete" not in original_haul:
            raise AssertionError("Autonomous competitor displaced active source owner: "
                                 +current_claim+" initial="+original_claim
                                 +" original_job="+original_haul)
    if claim_released:
        winning_actor=iris if selected=="Iris" else rowan
        winning_status=r.run(f"execute as {winning_actor} at @s run sable haul-status")
        if "Haul complete" not in winning_status:
            raise AssertionError("Shared claim vanished without verified completion: "+winning_status)
    # Sticky haulIssued status can refer to an earlier successful job.
    # Reject only two fresh assignments observed while a single exclusive
    # source claim is held; do not mistake historical status for concurrency.
    fresh_assignees=[
        name for name, value in observations.items()
        if choice_tick(value)>baseline[name] and "outcome=HAUL_ASSIGNED" in value
    ]
    if len(fresh_assignees)!=1:
        raise AssertionError("Expected one freshly assigned source owner: "
                             +str(fresh_assignees)+" statuses="+str(observations))
    for actor in (iris,rowan):
        r.run(f"execute as {actor} at @s run sable auto-work-off")
    pathlib.Path("gameplay-capture/autonomous-contention.json").write_text(json.dumps({
        "schema_version":1,"test":"dual_autonomous_source_selection",
        "source":shared_source,"wheat_precondition":wheat_before,"first_observed_assignee":selected,
        "owner_before":original_claim,"owner_after":current_claim,
        "claim_released_after_completion":claim_released,
        "policy_observations":observations,"initial_decision_ticks":baseline,
        "scope":"one exclusive active source claim; alternative job choice not tested"
    },indent=2)+"\n")
    print("AUTONOMOUS CONTENTION PASS: exactly one tick-policy assignment; exclusive claim retained")

    # Ensure the previous autonomous contention job really finished.
    # Disabling policy selection must not be mistaken for cancelling work.
    for actor, name in ((iris, "Iris"), (rowan, "Rowan")):
        for attempt in range(150):
            state = r.run(f"execute as {actor} at @s run sable haul-status")
            if "Haul complete" in state or "No active haul" in state:
                break
            time.sleep(1)
        else:
            raise AssertionError(f"{name} still has in-flight haul: {state}")

    # Separate alternate-work scenario: the job board should skip a claimed
    # source and allow an independent agent to discover an unclaimed one.
    # Claim is placed using real citizen hauling, never synthetic NBT state.
    # Retire wheat sources from the previous experiments so the board
    # has one claimed source and one unclaimed alternative, not stale offers.
    # Previously completed hauls leave wheat at destinations, which the
    # shared read-only board correctly advertises as new source offers.
    # Retire both previous sources AND destination fixtures so the next
    # experiment has only the deliberately constructed alternative offer.
    for old_source in ("3 101 1","3 101 7","4 101 8",
                       "9 101 7","9 101 8","9 101 1"):
        r.run(f"setblock {old_source} minecraft:barrel replace")
    primary="4 101 10"
    alternative="4 101 12"
    winner_dest="9 101 10"
    fallback_dest="9 101 12"
    for pos in (primary,alternative):
        r.contains(f'setblock {pos} minecraft:barrel{{Items:[{{Slot:0b,id:"minecraft:wheat",Count:2b}}]}} replace',
                   "Changed the block")
    for pos in (winner_dest,fallback_dest):
        r.run(f"setblock {pos} minecraft:barrel replace")
    r.contains(f"execute as {iris} at @s run sable haul {primary} {winner_dest}",
               "assigned wheat haul")
    # Keep Iris's genuinely-owned primary job in flight while Rowan chooses.
    # Otherwise Iris can finish between RCON commands and Rowan legitimately
    # select the nearer primary source after its claim is released.
    r.run(f"tp {iris} 0 101 1")
    first_claim=r.run(f"hearthboundclaims owner {primary}")
    if "belongs to" not in first_claim:
        raise AssertionError("Fixture failed to claim primary source: "+first_claim)
    # Focus the local eight-block discovery window on the alternative, not
    # earlier workshop stockpiles. No source is assigned directly to Rowan.
    r.run(f"tp {rowan} 4 101 11")
    r.contains(f"execute as {rowan} at @s run sable auto-work-source-discover {fallback_dest}",
               "Configured discover-source auto work")
    r.contains(f"execute as {rowan} at @s run sable auto-work-on","Auto work enabled")
    alternate_seen=False
    for _ in range(65):
        time.sleep(1)
        rowan_trace=r.run(f"execute as {rowan} at @s run sable auto-work-status")
        alternate_claim=r.run(f"hearthboundclaims owner {alternative}")
        if "haulIssued=true" in rowan_trace and "belongs to" in alternate_claim:
            alternate_seen=True
            break
        # A completed physical haul may release its claim before polling;
        # verify source debit and destination receipt rather than inferring
        # alternative choice from unrelated completed-job status.
        if "Haul complete" in r.run(f"execute as {rowan} at @s run sable haul-status"):
            source_nbt=r.run(f"data get block {alternative} Items")
            dest_nbt=r.run(f"data get block {fallback_dest} Items")
            if "Count: 1b" in source_nbt and "minecraft:wheat" in dest_nbt:
                alternate_seen=True
                break
    if not alternate_seen:
        raise AssertionError("Rowan did not claim alternate wheat source: policy="+rowan_trace+" alternative="+alternate_claim+" source="+r.run(f"data get block {alternative} Items")+" haul="+r.run(f"execute as {rowan} at @s run sable haul-status"))
    first_remaining=r.run(f"hearthboundclaims owner {primary}")
    if first_remaining not in (first_claim,f"No source claim at {primary}"):
        raise AssertionError("Alternate work overwrote existing claim: "+first_remaining)
    r.run(f"execute as {rowan} at @s run sable auto-work-off")
    pathlib.Path("gameplay-capture/alternative-work.json").write_text(json.dumps({
        "schema_version":1,
        "scope":"source discovery with another citizen's source already claimed",
        "primary":primary,"alternative":alternative,
        "primary_initial_owner":first_claim,
        "primary_owner_after":first_remaining,
        "alternative_owner":alternate_claim,
        "rowan_policy":rowan_trace,
        "alternative_selected":alternate_seen
    },indent=2)+"\n")
    print("ALTERNATIVE WORK PASS: autonomous citizen selected different unclaimed source")





