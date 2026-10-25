"""Fail closed if required fixtures or the real process hook did not execute."""
import pathlib
import re
import sys

def verify(text):
    for name in ("inventory_identity", "unpowered_millstone", "milling_motor_connection"):
        marker = "HEARTHBOUND_GAMETEST_PASS " + name
        if text.count(marker) != 1:
            raise ValueError(f"Expected exactly one pass marker: {name}")
    if text.count("HEARTHBOUND_SCRIPTED_MILLING_DECISION decision=PREPARE_MILLING") != 1:
        raise ValueError("Expected exactly one scripted milling decision")
    marker = "HEARTHBOUND_CITIZEN_CREDIT_FIXTURE_PASS "
    if text.count(marker) != 1:
        raise ValueError("Expected exactly one citizen attribution fixture pass")
    events = [line for line in text.splitlines() if "HEARTHBOUND_MILLSTONE_MUTATION " in line]
    if len(events) != 1:
        raise ValueError(f"Expected exactly one milling event, found {len(events)}")
    if not re.search(r"create:wheat_flourx[1-3](?=,|\])", events[0]):
        raise ValueError("Expected one to three flour from the wheat recipe")
    for field in ("input=minecraft:wheat ", "consumed=1 ",
                  "outputEvidence=positive_deltas", "researchCredit=false"):
        if field not in events[0]:
            raise ValueError(f"Missing milling evidence: {field}")

if __name__ == "__main__":
    verify(pathlib.Path(sys.argv[1]).read_text())
    print("Verified three runtime fixtures and exactly one milling observation")
