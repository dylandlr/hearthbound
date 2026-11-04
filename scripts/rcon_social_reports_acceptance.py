#!/usr/bin/env python3
"""Real Forge social report acceptance, following successful perception acceptance.

This fixture summons a second marked citizen and proves that knowledge delivery
requires explicit local communication, is recipient-owned, and never authorizes
Minecraft work. Uses actual source observation already collected by the server.
"""
import os
import json
import re
from real_forge_resource_schedule import plan,command as schedule_command,validate_log
import socket
import struct
import time
from pathlib import Path
from validate_forge_attention_pair import pair

def pkt(request_id, kind, value):
    body=struct.pack("<ii",request_id,kind)+value.encode()+b"\0\0"
    return struct.pack("<i",len(body))+body

def read_exact(sock,n):
    out=b""
    while len(out)<n:
        fragment=sock.recv(n-len(out))
        if not fragment: raise ConnectionError("RCON connection closed")
        out+=fragment
    return out

def get_response(sock,request_id):
    for _ in range(10):
        size=struct.unpack("<i",read_exact(sock,4))[0]
        if size<10 or size>1000000: raise ValueError("invalid RCON frame")
        frame=read_exact(sock,size)
        rid,kind=struct.unpack("<ii",frame[:8])
        if rid!=request_id: raise AssertionError("RCON request mismatch")
        result=frame[8:-2].decode(errors="replace")
        if result.strip(): return result
    raise AssertionError("missing RCON response")

with socket.create_connection(("127.0.0.1",25575),timeout=15) as sock:
    sock.settimeout(20)
    sock.sendall(pkt(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
    for _ in range(3):
        n=struct.unpack("<i",read_exact(sock,4))[0]
        frame=read_exact(sock,n)
        rid,_=struct.unpack("<ii",frame[:8])
        if rid==1:break
    else:raise AssertionError("RCON auth failed")
    counter=10
    def run(command):
        global counter
        sock.sendall(pkt(counter,2,command))
        result=get_response(sock,counter)
        counter+=1
        print(command,"=>",result,flush=True)
        return result

    # The v0.11.3 acceptance has stopped watching the source, leaving the
    # last direct evidence stale. A new explicit watch refreshes Sable's memory.
    run("hearthbound perception_watch 6 100 2")
    refreshed=False
    for _ in range(45):
        memory=run("hearthbound knowledge_source 6 100 2")
        if "status=KNOWN" in memory and "freshness=FRESH" in memory:
            refreshed=True
            break
        time.sleep(.2)
    if not refreshed: raise AssertionError("Sable did not obtain fresh direct evidence")

    # Unique marker makes entity selection independent of generated UUID.
    run('summon minecraft:villager 8 100 3 {CustomName:\'{"text":"HearthboundRecipient"}\',Tags:["hb_report_recipient"],ForgeData:{"hearthbound.citizen":1b}}')
    recipient="@e[type=minecraft:villager,tag=hb_report_recipient,limit=1]"
    before=run("hearthbound knowledge_report 6 100 2 "+recipient)
    if "status=UNKNOWN" not in before: raise AssertionError("Recipient had omniscient pre-share knowledge")
    sent=run("hearthbound knowledge_share 6 100 2 "+recipient)
    if "status=DELIVERED" not in sent or "action_authorized=false" not in sent:
        raise AssertionError("Explicit report not delivered: "+sent)
    report=run("hearthbound knowledge_report 6 100 2 "+recipient)
    if "status=REPORTED" not in report or "origin=REPORTED_DIRECT_FORGE_OBSERVATION" not in report or "action_authorized=false" not in report:
        raise AssertionError("Recipient report lost provenance: "+report)
    direct=run("hearthbound knowledge_source 6 100 2")
    if "origin=DIRECT_FORGE_OBSERVATION" not in direct:
        raise AssertionError("Sender's direct evidence overwritten by report")
    duplicate=run("hearthbound knowledge_share 6 100 2 "+recipient)
    if "status=DUPLICATE" not in duplicate:
        raise AssertionError("Duplicate report was not replay protected: "+duplicate)
    # Second citizen independently observes a different real chest, not
    # a shared global source cache or an incoming hearsay message.
    run("setblock 9 100 2 minecraft:chest replace")
    stocked=run('data merge block 9 100 2 {Items:[{Slot:0b,id:"minecraft:wheat",Count:3b}]}')
    if "modified" not in stocked.lower():
        raise AssertionError("Could not construct second physical source: "+stocked)
    sable="@e[type=minecraft:villager,name=Sable,limit=1]"
    sable_before=run("hearthbound citizen_memory 9 100 2 "+sable)
    receiver_before=run("hearthbound citizen_memory 9 100 2 "+recipient)
    if "status=UNKNOWN" not in sable_before or "status=UNKNOWN" not in receiver_before:
        raise AssertionError("Second source was known before direct citizen observation")
    observation=run("hearthbound citizen_observe 9 100 2 "+recipient)
    if "status=OBSERVED" not in observation or "wheat=3" not in observation or "action_authorized=false" not in observation:
        raise AssertionError("Recipient did not independently observe real chest: "+observation)
    receiver_after=run("hearthbound citizen_memory 9 100 2 "+recipient)
    sable_after=run("hearthbound citizen_memory 9 100 2 "+sable)
    if "status=KNOWN" not in receiver_after or "wheat=3" not in receiver_after or "origin=DIRECT_FORGE_OBSERVATION" not in receiver_after:
        raise AssertionError("Independent recipient memory not retained: "+receiver_after)
    if "status=UNKNOWN" not in sable_after:
        raise AssertionError("Sable learned recipient private observation without communication: "+sable_after)
    hearsay_only=run("hearthbound citizen_memory 6 100 2 "+recipient)
    if "status=UNKNOWN" not in hearsay_only:
        raise AssertionError("Incoming report improperly promoted to direct memory: "+hearsay_only)
    # Continuous Forge ticks must update only a specifically subscribed citizen.
    subscribed=run("hearthbound citizen_watch 9 100 2 "+recipient)
    if "status=REGISTERED" not in subscribed:
        raise AssertionError("Cannot subscribe citizen B: "+subscribed)
    first=None
    for _ in range(45):
        receipt=run("hearthbound citizen_watch_latest 9 100 2 "+recipient)
        if "CITIZEN_WATCH_RECEIPT" in receipt and "wheat=3" in receipt:
            first=receipt
            break
        time.sleep(.2)
    if first is None: raise AssertionError("No first per-citizen Forge tick receipt")
    unregistered=run("hearthbound citizen_watch_latest 9 100 2 "+sable)
    if "status=UNKNOWN" not in unregistered:
        raise AssertionError("Unsubscribed Sable saw recipient receipt")
    changed=run('data merge block 9 100 2 {Items:[{Slot:0b,id:"minecraft:wheat",Count:2b}]}')
    if "modified" not in changed.lower(): raise AssertionError("Watch fixture mutation failed")
    second=None
    for _ in range(45):
        receipt=run("hearthbound citizen_watch_latest 9 100 2 "+recipient)
        if "CITIZEN_WATCH_RECEIPT" in receipt and "wheat=2" in receipt:
            second=receipt
            break
        time.sleep(.2)
    if second is None: raise AssertionError("No second per-citizen Forge tick receipt")
    updated=run("hearthbound citizen_memory 9 100 2 "+recipient)
    if "wheat=2" not in updated: raise AssertionError("Recipient memory not refreshed")
    removed=run("hearthbound citizen_unwatch 9 100 2 "+recipient)
    if "removed=true" not in removed: raise AssertionError("Citizen watch not removed")
    # Restore the expected restart fixture and directly observe the new state.
    restored=run('data merge block 9 100 2 {Items:[{Slot:0b,id:"minecraft:wheat",Count:3b}]}')
    if "modified" not in restored.lower(): raise AssertionError("Restore fixture failed")
    restored_read=run("hearthbound citizen_observe 9 100 2 "+recipient)
    if "wheat=3" not in restored_read or "status=OBSERVED" not in restored_read:
        raise AssertionError("Recipient failed to observe restored state")
    # Attention budget: two subscriptions for one citizen, but only one
    # source may be inspected per five-tick interval. Fair scheduling must
    # eventually provide separate real Forge receipts for both sources.
    installed=run("setblock 10 100 2 minecraft:chest replace")
    if "changed" not in installed.lower():
        raise AssertionError("Could not install attention comparison source")
    extra=run('data merge block 10 100 2 {Items:[{Slot:0b,id:"minecraft:wheat",Count:1b}]}')
    if "modified" not in extra.lower():
        raise AssertionError("Could not stock attention comparison source")
    started=run("hearthbound citizen_log_start")
    if "status=STARTED" not in started:
        raise AssertionError("Could not enable durable Forge attention journal: "+started)
    for pos in ("9 100 2", "10 100 2"):
        response=run("hearthbound citizen_watch "+pos+" "+recipient)
        if "status=REGISTERED" not in response:
            raise AssertionError("Attention subscription failed: "+response)
    budget=run("hearthbound citizen_attention "+recipient)
    if "subscriptions=2" not in budget or "budget=1" not in budget or "interval_ticks=5" not in budget:
        raise AssertionError("Citizen attention limits absent: "+budget)
    # Opportunity records are emitted before the chosen source's inventory is read.
    # Candidate membership must be drawn from subscriptions, not world truth.
    opportunity=None
    for _ in range(45):
        result=run("hearthbound citizen_opportunity_latest")
        if ("ATTENTION_OPPORTUNITY schema=hearthbound.forge-attention-opportunity.v1" in result
                and "candidate_count=2" in result
                and "9,100,2" in result and "10,100,2" in result):
            opportunity=result
            break
        time.sleep(.2)
    if opportunity is None:
        raise AssertionError("Missing real Forge pre-inspection two-source opportunity")
    if "inventory_read=false" not in opportunity or "action_authorized=false" not in opportunity:
        raise AssertionError("Opportunity record may not contain world truth or action authority")
    if "budget=1" not in opportunity or "policy=LEAST_RECENTLY_SAMPLED" not in opportunity:
        raise AssertionError("Opportunity contract missing original attention baseline")
    if "wheat=" in opportunity or "state=" in opportunity:
        raise AssertionError("Source state leaked into decision-opportunity log")
    # The latest two independently queried records may race the next server
    # tick, so require exact observer/source/tick attribution before saving.
    matched=None
    for _ in range(70):
        proposed=run("hearthbound citizen_opportunity_latest")
        observed=run("hearthbound citizen_outcome_latest")
        try:
            candidate=pair(proposed,observed)
        except ValueError:
            time.sleep(.1)
            continue
        if len(candidate["opportunity"]["candidates"])==2:
            matched=(proposed,observed)
            break
        time.sleep(.1)
    if matched is None:
        raise AssertionError("Could not capture an attributed choice/outcome pair")
    opportunity,outcome=matched
    Path("real-attention-opportunity.txt").write_text(opportunity+"\n")
    Path("real-attention-outcome.txt").write_text(outcome+"\n")
    seen=set()
    for _ in range(60):
        for pos,expected in (("9 100 2","wheat=3"),("10 100 2","wheat=1")):
            result=run("hearthbound citizen_watch_latest "+pos+" "+recipient)
            if "CITIZEN_WATCH_RECEIPT" in result and expected in result:
                seen.add(pos)
        if len(seen)==2: break
        time.sleep(.2)
    if len(seen)!=2:
        raise AssertionError("Fair selective attention did not sample both subscriptions: "+str(seen))
    # Optional research-only intervention schedule, after the frozen
    # two-source acceptance has passed and before recording is stopped.
    # These are OPERATOR RCON mutations, not citizen actions.
    schedule_variant=os.environ.get("HEARTHBOUND_RESOURCE_SCHEDULE","baseline")
    if schedule_variant=="seeded-v1":
        configured_seed=os.environ["HEARTHBOUND_WORLD_SEED"]
        planned=plan(configured_seed)
        executions=[]
        for step in planned["steps"]:
            before=run("time query gametime")
            hits=re.findall(r"\\d+",before)
            if not hits:
                raise AssertionError("Minecraft game tick not returned: "+before)
            tick_before=int(hits[-1])
            response=run(schedule_command(step))
            if "modified" not in response.lower():
                raise AssertionError("Real chest mutation failed: "+response)
            after=run("time query gametime")
            hits=re.findall(r"\\d+",after)
            if not hits:
                raise AssertionError("Minecraft post-mutation tick missing: "+after)
            tick_after=int(hits[-1])
            executions.append({
                "index":step["index"],"source":step["source"],"wheat":step["wheat"],
                "tick_before":tick_before,"tick_after":tick_after,
                "status":"RCON_MODIFIED"})
            time.sleep(step["delay_seconds"])
        actual={
            "schema":planned["schema"],"origin":"REAL_FORGE_RCON",
            "configured_world_seed":configured_seed,
            "schedule_sha256":planned["sha256"],
            "executions":executions,
            "counterfactual_outcomes_inferred":False}
        verified=validate_log(actual)
        Path("real-resource-schedule.json").write_text(json.dumps(actual,sort_keys=True,indent=2)+"\\n")
        Path("verified-resource-schedule.json").write_text(json.dumps(verified,sort_keys=True,indent=2)+"\\n")
        print("REAL_FORGE_RESOURCE_SCHEDULE_PASS steps="+str(len(executions)),flush=True)
    elif schedule_variant!="baseline":
        raise AssertionError("Unsupported resource intervention schedule variant")
    other_unknown=run("hearthbound citizen_memory 10 100 2 "+sable)
    if "status=UNKNOWN" not in other_unknown:
        raise AssertionError("Attention sampling leaked evidence to Sable")
    for pos in ("9 100 2","10 100 2"):
        result=run("hearthbound citizen_unwatch "+pos+" "+recipient)
        if "removed=true" not in result:
            raise AssertionError("Failed to remove attention watch: "+result)
    stopped=run("hearthbound citizen_log_stop")
    if "status=STOPPED" not in stopped or "records=" not in stopped:
        raise AssertionError("Durable experiment log did not stop cleanly: "+stopped)
    status=run("hearthbound citizen_log_status")
    if "last_error=NONE" not in status:
        raise AssertionError("Durable experiment log failed to append: "+status)
    sable_still_unknown=run("hearthbound citizen_memory 9 100 2 "+sable)
    if "status=UNKNOWN" not in sable_still_unknown:
        raise AssertionError("Sable acquired unrelated private memory")
    run("hearthbound perception_unwatch 6 100 2")
    print("REAL_FORGE_SOCIAL_REPORT_ACCEPTANCE_PASS",flush=True)
