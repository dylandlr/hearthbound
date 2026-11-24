#!/usr/bin/env python3
"""Reproduce descriptive live metrics from the retained original evidence ZIPs."""
import argparse
import collections
import json
from pathlib import Path
import statistics
import zipfile


def analyze(folder):
    rows=[]
    for world in (22001,22002):
        for arm in ('authored','neural','untrained'):
            path=folder/f'shared-service-{world}-{arm}.zip'
            with zipfile.ZipFile(path) as z:
                names=[n for n in z.namelist() if n.endswith('shared-service-acceptance.json')]
                if len(names)!=1: raise ValueError('Missing/duplicate evidence: '+str(path))
                r=json.loads(z.read(names[0]))
            if (r['status']!='passed_live_and_restart' or r['world']!=world or r['arm']!=arm
                    or r['commit']!='495938dc4a31befd31afb224b109474ae4d3c296' or r['origin']!='REAL_FORGE_CREATE'):
                raise ValueError('Incomplete or mismatched slot; retain failure rather than aggregate as successful')
            ev=r['records'];cut=r['start_tick']+r['horizon_ticks']
            jobs=[e for e in ev if e['type']=='PRODUCTION_SETTLED'];scored=[e for e in jobs if e['tick']<=cut]
            duration=[e['duration_ticks']/20 for e in ev if e['type']=='SERVICE_SETTLED' and e['outcome']=='VERIFIED_TRANSFER']
            cancels=collections.Counter(e.get('reason') for e in ev if e['type'] in ('OPTION_CANCELLED','ARBITRATION_REFUSED'))
            rows.append(dict(world=world,arm=arm,score=r['score'],demand_covered_at_deadline=sum(min(n,t) for n,t in zip(r['score']['per_site'],(5,4))),
                final_flour=[i['items'].get('create:wheat_flour',0) for i in r['after']['outputs']],final_seeds=[i['items'].get('minecraft:wheat_seeds',0) for i in r['after']['outputs']],
                final_source_wheat=[i['items'].get('minecraft:wheat',0) for i in r['after']['sources']],jobs_total=len(jobs),jobs_scored=len(scored),
                distinct_producers=len({j['citizen'] for j in scored}),per_citizen_output=[c['verified_output_units'] for c in r['terminal']['citizens']],
                productive_duration_seconds=duration,refusals_cancellations=dict(cancels),decision_count=r['replayed_policy_choices'],model_sha256=r['terminal']['model_sha256'],
                neural_weight_updates=r['terminal']['neural_weight_updates'],status=r['status'],changes=r['changes'],held=r['terminal']['held'],active_commitments=r['terminal']['active_commitments']))
    return dict(tested_commit='495938dc4a31befd31afb224b109474ae4d3c296',origin='REAL_FORGE_CREATE',run_id=45494997186,rows=rows,
        total_replayed_decisions=sum(r['decision_count'] for r in rows),neural_replayed_decisions=sum(r['decision_count'] for r in rows if r['arm']=='neural'),
        total_real_jobs=sum(r['jobs_total'] for r in rows),neural_real_jobs=sum(r['jobs_total'] for r in rows if r['arm']=='neural'),
        total_delivered_flour=sum(sum(r['final_flour']) for r in rows),total_delivered_seeds=sum(sum(r['final_seeds']) for r in rows),
        means={arm:dict(deadline_flour=statistics.mean(r['score']['output'] for r in rows if r['arm']==arm),settled_cost=statistics.mean(r['score']['settled_personal_cost'] for r in rows if r['arm']==arm),
            messages=statistics.mean(r['score']['sends'] for r in rows if r['arm']==arm)) for arm in ('neural','untrained','authored')})


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=analyze(args.input);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
