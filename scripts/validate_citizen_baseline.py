#!/usr/bin/env python3
"""Validate real citizen-baseline evidence without conflating priors and policies."""
import argparse,json,pathlib,re
EXPECTED={"Sable","Rowan","Iris"}
def validate(data):
    residents=data.get("residents",{})
    if set(residents)!=EXPECTED: raise AssertionError("Expected exactly three named citizens")
    identities=[]
    for name,entry in residents.items():
        evidence=entry.get("entity_uuid_evidence","")
        uuid=re.search(r"\[I;\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\]",evidence)
        if not uuid: raise AssertionError(f"{name}: missing vanilla UUID int-array evidence")
        identities.append(uuid.group(0))
        profile=entry.get("instinct_profile","")
        if "starting priors only" not in profile or "INSTINCT" not in profile:
            raise AssertionError(f"{name}: no truthful instinct inspection")
        for trait in ("food","shelter","danger","combat","exploration","cooperation"):
            m=re.search(r"\b"+trait+r"=(\d+)\b",profile)
            if not m or not 25<=int(m.group(1))<=75: raise AssertionError(f"{name}: invalid {trait}")
    if len(set(identities))!=3: raise AssertionError("UUID collision")
    if data.get("schema_version",0)>=2:
        haul=residents["Rowan"].get("independent_haul",{})
        if not haul.get("auto_assigned") or not haul.get("completed") or "minecraft:wheat" not in haul.get("destination_evidence","") or "Count: 3b" not in haul.get("source_evidence",""):
            raise AssertionError("No verified Rowan tick-selected physical haul")
    return True
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path")
    a=p.parse_args()
    validate(json.loads(pathlib.Path(a.path).read_text()))
    print("PASS: 3 independent citizen identities, bounded priors; no job autonomy asserted")
