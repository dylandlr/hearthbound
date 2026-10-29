"""Fail closed if required fixtures or the real process hook did not execute."""
import pathlib
import re
import sys

def verify(text):
    for name in ("inventory_identity", "unpowered_millstone", "milling_motor_connection", "consecutive_real_millings", "persistent_citizen_registry", "visible_citizen_embodiment", "scripted_citizen_movement", "real_citizen_pathfinding", "citizen_walks_and_supplies_mill", "citizen_supply_recovery_contract", "citizen_supply_interruption_boundaries", "millstone_output_extraction_conserves_items", "citizen_collects_real_millstone_output"):
        marker = "HEARTHBOUND_GAMETEST_PASS " + name
        if text.count(marker) != 1:
            raise ValueError(f"Expected exactly one pass marker: {name}")
    if text.count("HEARTHBOUND_SCRIPTED_WORK_LOOP action=ACTIVATE_POWER") != 1:
        raise ValueError("Expected exactly one scripted work-loop motor activation")
    if text.count("HEARTHBOUND_SCRIPTED_MILLING_DECISION decision=PREPARE_MILLING") != 1:
        raise ValueError("Expected exactly one scripted milling decision")
    marker = "HEARTHBOUND_CITIZEN_CREDIT_FIXTURE_PASS "
    if text.count(marker) != 1:
        raise ValueError("Expected exactly one citizen attribution fixture pass")
    if text.count("HEARTHBOUND_SCRIPTED_WORK_LOOP action=SUPPLY_WHEAT conserved=true") != 1:
        raise ValueError("Expected conserved wheat input")
    events = [line for line in text.splitlines() if "HEARTHBOUND_MILLSTONE_MUTATION " in line]
    if len(events) != 3:
        raise ValueError(f"Expected three real milling events, found {len(events)}")
    if text.count("HEARTHBOUND_CITIZEN_REAL_WALK_SUPPLY_PASS ") != 1:
        raise ValueError("Expected physical citizen navigation followed by real Create wheat supply")
    if text.count("HEARTHBOUND_REAL_CITIZEN_NAVIGATION_PASS ") != 1:
        raise ValueError("Expected physical villager pathfinding proof")
    if text.count("HEARTHBOUND_TWO_REAL_MILLINGS_PASS ") != 1:
        raise ValueError("Missing unique consecutive-real-millings verification")
    if not re.search(r"create:wheat_flourx[1-3](?=,|\])", events[0]):
        raise ValueError("Expected one to three flour from the wheat recipe")
    for field in ("input=minecraft:wheat ", "consumed=1 ",
                  "outputEvidence=positive_deltas", "researchCredit=false"):
        if any(field not in event for event in events):
            raise ValueError(f"Missing milling evidence: {field}")

if __name__ == "__main__":
    verify(pathlib.Path(sys.argv[1]).read_text())
    print("Verified four runtime fixtures and three real milling events")
