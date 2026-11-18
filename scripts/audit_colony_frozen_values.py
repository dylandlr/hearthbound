"""Exploratory paired simulator branches at frozen policies' first eligible waits."""
import argparse
from collections import Counter
import copy
import gzip
import hashlib
import json
from pathlib import Path

from colony_task_env import Env, scripted_balance
from colony_allocation_alias import choose, decision_mask
from train_colony_task_allocation import Network, REGIMES


def context(obs):
    """Coarse observable coverage proxy, deliberately not a sufficient state."""
    site = next((i for i in range(4) if obs[12 + 8*i] == 1), -1)
    balance = obs[1] + obs[3] / 4 - obs[2] - obs[4] / 4
    return (int(obs[5]), site, min(3, int(obs[0]*4)),
            (balance > 0) - (balance < 0),
            *(int(obs[9 + 8*i] == 1 and obs[10 + 8*i] > 0) for i in range(4)))


def finish(world, actions, model, prune):
    """Apply one simultaneous decision batch, then resume the same frozen team."""
    fork = copy.deepcopy(world)
    fork.step(actions)
    while not fork.done:
        decisions = {a: choose(model, fork.obs(a), prune) for a in fork.ready()}
        fork.step(decisions)
    result = fork.metrics()
    assert result['conservation_residual_A'] == result['conservation_residual_B'] == 0
    return result['produced']


def audit(model, world, prune, coverage):
    before = model.digest(), model.updates
    sampled, records = set(), []
    while not world.done:
        observations = {a: tuple(world.obs(a)) for a in world.ready()}
        actions = {a: choose(model, o, prune) for a, o in observations.items()}
        for agent, obs in observations.items():
            if agent in sampled or actions[agent] != 0 or world.horizon-world.tick < 16:
                continue
            # Evaluator-only material bound excludes provably exhausted episodes.
            # It never enters the policy or alternative selector.
            metrics = world.metrics()
            if metrics['produced'] >= metrics['attainable_material_bound']:
                continue
            alternative = scripted_balance(obs, agents=world.agents)
            if alternative == 0 or not decision_mask(obs, prune)[alternative]:
                continue
            sampled.add(agent)
            q = model.values(obs)
            changed = dict(actions, **{})
            changed[agent] = alternative
            original = finish(world, actions, model, prune)
            intervention = finish(world, changed, model, prune)
            counts = coverage.get(context(obs), Counter())
            records.append(dict(agent=agent, tick=world.tick, alternative=alternative,
                original_final_products=original, intervention_final_products=intervention,
                difference=intervention-original, q_wait=float(q[0]),
                q_alternative=float(q[alternative]),
                coarse_context_samples=sum(counts.values()),
                coarse_wait_samples=counts[0], coarse_alternative_samples=counts[alternative]))
        world.step(actions)
    assert before == (model.digest(), model.updates)
    return records


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--evidence-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise ValueError('Refuse to overwrite an audit')
    protocol = dict(schema='hearthbound.frozen-value-audit.v0.6', exploratory=True,
        worlds=list(range(9100000,9100004)), regimes=list(REGIMES), seeds=[17,23,41],
        policies=['legacy_online','offline_td','offline_greedy5'], prune=[False,True],
        sampling='first eligible WAIT per worker per episode; at least16 ticks left; below material bound',
        intervention='one worker takes equal-information balanced-script option; others unchanged; frozen continuation',
        limitation='reused diagnostic worlds; selected waits only; coarse coverage is not exact state support',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.with_suffix('.protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    rows, hashes = [], {}
    for seed in protocol['seeds']:
        coverage = {}
        for line in gzip.decompress((args.evidence_dir/f'corpus-{seed}.jsonl.gz').read_bytes()).splitlines():
            item = json.loads(line)
            coverage.setdefault(context(item['observation']),Counter())[item['action']] += 1
        for policy in protocol['policies']:
            filename = f'legacy-trained-{seed}.json' if policy=='legacy_online' else f'{policy}-{seed}.json'
            model=Network.load(args.evidence_dir/filename)
            hashes[f'{seed}:{policy}']=model.digest()
            for regime in protocol['regimes']:
                for world_seed in protocol['worlds']:
                    for prune in protocol['prune']:
                        records=audit(model,Env(world_seed,regime=regime),prune,coverage)
                        rows.extend(dict(seed=seed,policy=policy,regime=regime,world_seed=world_seed,
                                         pruned=prune,**r) for r in records)
    summary={}
    for policy in protocol['policies']:
        for prune in protocol['prune']:
            own=[r for r in rows if r['policy']==policy and r['pruned']==prune]
            summary[f'{policy}:{prune}']=dict(selected_waits=len(own),
                beneficial=sum(r['difference']>0 for r in own), harmful=sum(r['difference']<0 for r in own),
                unchanged=sum(r['difference']==0 for r in own),
                mean_difference=sum(r['difference'] for r in own)/max(1,len(own)),
                no_coarse_alternative_samples=sum(r['coarse_alternative_samples']==0 for r in own))
    args.output.write_text(json.dumps(dict(protocol=protocol,parameter_hashes=hashes,
                                          summary=summary,records=rows),indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
