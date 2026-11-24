#!/usr/bin/env python3
"""Keep every preregistered world/policy slot, including absent/failed trials."""
import argparse
import json
from pathlib import Path
import os
from rcon_village_economy_acceptance import ARMS, WORLDS, SCHEMA


def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    observed={}
    for path in a.input.rglob('village-acceptance.json'):
        value=json.loads(path.read_text()); key=(value.get('world'),value.get('arm'))
        if key in observed: raise AssertionError('Duplicate native slot: '+str(key))
        observed[key]=value
    slots=[]; expected=os.environ.get('HEARTHBOUND_EXPECTED_COMMIT')
    for world in WORLDS:
        for arm in ARMS:
            v=observed.get((world,arm),{}); valid=(v.get('schema')==SCHEMA and (not expected or v.get('commit')==expected))
            slots.append(dict(world=world,arm=arm,status=v.get('status','missing'),valid_identity=valid,
                error=v.get('error','')[:3000],milestone_passed=v.get('milestone_passed',False),
                milestone_checks=v.get('milestone_checks',{}),horizon_totals=v.get('horizon_status',{}).get('totals',{}),
                physical=v.get('physical_audit',{}),policy=v.get('policy_audit',{}),commit=v.get('commit')))
    passed=all(s['valid_identity'] and s['status']=='passed_live_and_restart' for s in slots)
    milestone=all(s['milestone_passed'] for s in slots if s['arm']=='adaptive')
    pairs=[]
    for world in WORLDS:
        pair={s['arm']:s for s in slots if s['world']==world}
        if all(s['status']=='passed_live_and_restart' for s in pair.values()):
            pairs.append(dict(world=world,adaptive_minus_authored_meals=pair['adaptive']['horizon_totals'].get('meals',0)-pair['authored']['horizon_totals'].get('meals',0),
                              adaptive_minus_authored_bread=pair['adaptive']['horizon_totals'].get('bread_baked',0)-pair['authored']['horizon_totals'].get('bread_baked',0)))
    result=dict(schema='hearthbound.village-cohort.v0.23',commit=expected,planned_slots=4,independent_worlds=2,
                all_integrity_and_restart_passed=passed,adaptive_milestone_passed=milestone,slots=slots,paired_descriptive_deltas=pairs,
                interpretation='Bounded integration cohort; same seed does not fix UUIDs, loot RNG or scheduling. No population learning/communication advantage claim.')
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2))
    if not passed or not milestone: raise SystemExit('Village cohort gate incomplete; all four slots retained')


if __name__=='__main__': main()
