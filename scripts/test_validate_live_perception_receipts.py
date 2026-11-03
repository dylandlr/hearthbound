#!/usr/bin/env python3
"""Rejection tests for live receipt protocol. Synthetic fixtures are NOT gameplay."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("validate_live_perception_receipts.py")
spec=importlib.util.spec_from_file_location("live_receipts",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

UUID="00000000-0000-0000-0000-000000000001"
def fixture(revision=1,tick=5,state="EMPTY",wheat=0,source="1,2,3"):
    return ("PERCEPTION_RECEIPT schema=hearthbound.live-perception-receipt.v1"
            " dimension=minecraft:overworld source="+source+
            " revision="+str(revision)+" tick="+str(tick)+
            " state="+state+" wheat="+str(wheat)+
            " observer="+UUID+
            " evidence=REAL_FORGE_SOURCE_OBSERVATION action_authorized=false")

def must_fail(line):
    try:m.validate_lines([line])
    except ValueError:return
    raise AssertionError("Invalid real-world claim accepted: "+line)

def main():
    clean=[fixture(),fixture(2,10,"AVAILABLE",4)]
    verified=m.validate_lines(["random prefix",*clean])
    assert verified["receipts"]==2
    assert verified["distinct_sources"]==1
    assert verified["task_execution_authorized"] is False
    assert verified["events"][1]["wheat"]==4
    for bad in (
        fixture(state="AVAILABLE"),
        fixture(state="UNKNOWN"),
        fixture(wheat=2),
        fixture(revision=0),
        fixture(tick=-1),
        fixture(source="x,y,z"),
        fixture().replace("action_authorized=false","action_authorized=true"),
        fixture().replace("REAL_FORGE_SOURCE_OBSERVATION","SIMULATED_ONLY"),
        fixture().replace(UUID,"not-a-uuid"),
        fixture()+" revision=3",
    ):must_fail(bad)
    for corrupt in (
        [fixture(1,5),fixture(1,10)],
        [fixture(1,5),fixture(3,10)],
        [fixture(1,10),fixture(2,5)],
    ):
        try:m.validate_lines(corrupt)
        except ValueError:pass
        else:raise AssertionError("Bad stream accepted")
    # Real receipt exporter is explicitly an operator-only read-only command.
    mod=(Path(__file__).resolve().parents[1]/
         "src/main/java/dev/hearthbound/HearthboundMod.java").read_text()
    for command in ("perception_watch","perception_unwatch","perception_receipts"):
        assert 'Commands.literal("'+command+'")' in mod
    monitor=(Path(__file__).resolve().parents[1]/
             "src/main/java/dev/hearthbound/world/LivePerceptionReceipts.java").read_text()
    assert "SourceWheatObservation.inspect(" in monitor
    assert "hasChunkAt(source)" in monitor
    assert "SAMPLE_EVERY_TICKS = 5L" in monitor
    assert "MAX_WATCHES_PER_LEVEL = 12" in monitor
    print("PASS strict Forge receipt replay parsing, revision order, stale/unknown rejection and read-only probe wiring")

if __name__=="__main__":main()
