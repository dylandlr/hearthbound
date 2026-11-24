#!/usr/bin/env python3
"""Retain every declared live slot, including missing/failed artifacts."""
import argparse
import json
import os
from pathlib import Path


def summarize(root,commit):
    slots=[]
    for world in (22001,22002):
        for arm in ('neural','untrained','authored'):
            found=list((root/f'shared-service-{world}-{arm}').rglob('shared-service-acceptance.json'))
            slot=dict(world=world,arm=arm,status='missing',integrity_passed=False,milestone_passed=False)
            if len(found)==1:
                record=json.loads(found[0].read_text()); slot.update(status=record.get('status'),score=record.get('score'),
                    error=record.get('error'),model_sha256=record.get('terminal',{}).get('model_sha256'),
                    replayed_choices=record.get('replayed_policy_choices'),responded_to_later_demand=record.get('responded_to_later_demand'))
                slot['integrity_passed']=(record.get('status')=='passed_live_and_restart' and record.get('commit')==commit
                    and record.get('arm')==arm and record.get('world')==world and record.get('origin')=='REAL_FORGE_CREATE')
                slot['milestone_passed']=slot['integrity_passed'] and record.get('milestone_passed') is True
            elif len(found)>1: slot['status']='duplicate_artifacts'
            slots.append(slot)
    integrity=sum(s['integrity_passed'] for s in slots)
    neural=sum(s['milestone_passed'] for s in slots if s['arm']=='neural')
    return dict(schema='hearthbound.shared-service-live-summary.v0.22',commit=commit,planned_slots=6,slots=slots,
                integrity_passed=integrity,neural_milestone_passed=neural,neural_planned=2,
                passed=integrity==6 and neural==2,independent_worlds=2,claim='bounded integration comparison; no population or causal communication effect estimate')


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=summarize(args.input,os.environ['HEARTHBOUND_EXPECTED_COMMIT']);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__': main()
