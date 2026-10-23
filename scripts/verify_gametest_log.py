"""Fail closed if required fixtures or the real process hook did not execute."""
import pathlib
import sys

def verify(text):
    for name in ("inventory_identity", "unpowered_millstone", "milling_fixture_rotation"):
        marker = "HEARTHBOUND_GAMETEST_PASS " + name
        if text.count(marker) != 1:
            raise ValueError(f"Expected exactly one pass marker: {name}")
    events = [line for line in text.splitlines() if "HEARTHBOUND_MILLSTONE_MUTATION " in line]
    if len(events) != 1:
        raise ValueError(f"Expected exactly one milling event, found {len(events)}")
    for field in ("input=minecraft:wheat ", "consumed=1 ", "create:wheat_flourx1",
                  "outputEvidence=positive_deltas", "researchCredit=false"):
        if field not in events[0]:
            raise ValueError(f"Missing milling evidence: {field}")

if __name__ == "__main__":
    verify(pathlib.Path(sys.argv[1]).read_text())
    print("Verified three runtime fixtures and exactly one milling observation")
