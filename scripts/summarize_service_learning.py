#!/usr/bin/env python3
"""Descriptive world-block uncertainty for a fully declared synthetic cohort."""
import argparse
import json
from pathlib import Path
import numpy as np


def summarize(result):
    protocol=result['protocol']; rows=result['evaluation']; seeds=protocol['training_seeds']; worlds=protocol['evaluation_worlds']
    arms=('trained','untrained','authored'); expected={(w,s,a) for w in worlds for s in seeds for a in arms}
    keys=[(r['seed'],r['training_seed'],r['arm']) for r in rows]
    if len(keys)!=len(set(keys)) or set(keys)!=expected:
        raise ValueError('Missing, duplicate or undeclared evaluation slots; do not omit failures')
    if any(r['origin']!='SYNTHETIC' or r['material_conserved'] is not True for r in rows):
        raise ValueError('Invalid receipt origin or failed material conservation')
    perseed=[dict(seed=s,mean_output={a:float(np.mean([r['output'] for r in rows if r['training_seed']==s and r['arm']==a])) for a in arms}) for s in seeds]
    diffs=[]
    for w in worlds:
        means={a:np.mean([r['output'] for r in rows if r['seed']==w and r['arm']==a]) for a in arms}
        diffs.append(means['trained']-means['authored'])
    rng=np.random.default_rng(22022); boot=[float(np.mean(rng.choice(diffs,len(diffs),replace=True))) for _ in range(10000)]
    return dict(planned_slots=len(expected),completed_slots=len(rows),independent_evaluation_worlds=len(worlds),training_seeds=len(seeds),per_seed=perseed,
                mean_output={a:float(np.mean([r['output'] for r in rows if r['arm']==a])) for a in arms},
                trained_minus_authored_world_block_mean=float(np.mean(diffs)),conditional_world_bootstrap_95=np.quantile(boot,[.025,.975]).tolist(),
                bootstrap_seed=22022,bootstrap_resamples=10000,uncertainty_scope='24 worlds, averaged over these three fixed trained networks; not uncertainty over all training runs',
                receipt_origin='SYNTHETIC',live_claim=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=summarize(json.loads(args.input.read_text()));args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
