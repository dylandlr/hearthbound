"""Train action-alias removal consistently in exploration, exploitation and backup."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import numpy as np
import train_colony_task_allocation as base
from colony_task_env import Env
from colony_allocation_alias import choose, decision_mask


class MaskedNetwork(base.Network):
    def __init__(self, seed, prune):
        super().__init__(seed)
        self.prune = prune
        self.backup_mask = False

    def values(self, observations):
        values = super().values(observations)
        if not self.backup_mask:
            return values
        return np.where([decision_mask(o,self.prune) for o in observations],values,-np.inf)

    def greedy(self, obs):
        return choose(self,obs,self.prune)

    def update(self,batch,target,rate=.001):
        self.backup_mask=True
        try:
            super().update(batch,target,rate)
        finally:
            self.backup_mask=False


def train(seed,episodes,prune):
    if episodes<5: raise ValueError('At least five episodes required')
    model=MaskedNetwork(seed,prune)
    target=copy.deepcopy(model)
    rng=random.Random(base.stable_seed('v07-exploration',seed))
    replay_rng=random.Random(base.stable_seed('v07-replay',seed))
    replay=[]
    for episode in range(episodes):
        epsilon=.08+.82*max(0,1-episode/(episodes*.8))
        def policy(agent,obs):
            valid=[i for i,ok in enumerate(decision_mask(obs,prune)) if ok]
            return rng.choice(valid) if rng.random()<epsilon else model.greedy(obs)
        def remember(t):
            assert decision_mask(t['observation'],prune)[t['action']]
            replay.append(t)
            if len(replay)>20000: del replay[:2000]
        def learn():
            if episode<4: return
            assert len(replay)>=32
            model.update(replay_rng.sample(replay,32),target)
            if model.updates%200==0:
                target.parameters={k:v.copy() for k,v in model.parameters.items()}
        base.run_episode(policy,Env(base.stable_seed('v07-world',seed,episode)),
                         on_transition=remember,on_tick=learn)
    assert model.updates==(episodes-4)*64
    return model


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--episodes',type=int,default=600)
    p.add_argument('--seeds',default='17,23,41')
    p.add_argument('--worlds',type=int,default=40)
    p.add_argument('--output-dir',type=Path,required=True)
    args=p.parse_args()
    seeds=[int(s) for s in args.seeds.split(',')]
    if len(set(seeds))!=len(seeds) or args.worlds<1 or args.episodes<5: p.error('Invalid dimensions')
    root=args.output_dir
    if root.exists() and any(root.iterdir()): raise ValueError('Nonempty output')
    root.mkdir(parents=True,exist_ok=True)
    protocol=dict(schema='hearthbound.online-masked-allocation.v0.7',seeds=seeds,
        episodes=args.episodes,worlds=list(range(9200000,9200000+args.worlds)),
        regimes=list(base.REGIMES),updates_each=(args.episodes-4)*64,
        settings=base.TRAINING_SETTINGS,warmup_episodes=4,
        treatment='alias mask in exploration, greedy selection and DoubleDQN successor argmax',
        unchanged='WAIT, reward, observations, architecture, worlds, initialization, tick and optimizer budgets',
        limitation='on-policy visitation and replay contents change with action design',
        primary='pruned minus full standard; >=0.25 batches and crossed interval lower>0',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        original_sources=base.source_manifest(),numpy=np.__version__)
    (root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    rows=[]
    for seed in seeds:
        for prune in (False,True):
            model=train(seed,args.episodes,prune)
            name='pruned' if prune else 'full'
            path=root/f'{name}-{seed}.json'
            model.save(path)
            saved=json.loads(path.read_text())
            saved['online_mask_contract']=dict(prune=prune,protocol=protocol)
            path.write_text(json.dumps(saved,separators=(',',':'))+'\n')
            loaded=base.Network.load(path)
            assert loaded.digest()==model.digest()
            frozen=MaskedNetwork(seed,prune)
            frozen.parameters=loaded.parameters
            before=frozen.digest()
            for regime in base.REGIMES:
                for world_seed in protocol['worlds']:
                    for label in (name,'scripted_balance'):
                        policy=(lambda a,o:frozen.greedy(o)) if label==name else (lambda a,o:base.scripted_balance(o))
                        metrics,_=base.run_episode(policy,Env(world_seed,regime=regime))
                        rows.append(dict(seed=seed,arm=name,policy=label,world_seed=world_seed,regime=regime,**metrics))
            assert frozen.digest()==before and frozen.updates==0
            print(json.dumps(dict(seed=seed,arm=name,updates=model.updates)),flush=True)
    summary={}
    for regime in base.REGIMES:
        own=[r for r in rows if r['regime']==regime]
        lookup={(r['seed'],r['world_seed'],r['policy']):r['produced'] for r in own if r['policy']!='scripted_balance'}
        matrix=[[lookup[s,w,'pruned']-lookup[s,w,'full'] for w in protocol['worlds']] for s in seeds]
        interval=base.crossed_interval(matrix)
        summary[regime]=dict(means={n:float(np.mean([r['produced'] for r in own if r['policy']==n])) for n in ('full','pruned','scripted_balance')},
            difference=float(np.mean(matrix)),interval=interval,per_seed=[float(np.mean(x)) for x in matrix],
            criterion_met=float(np.mean(matrix))>=.25 and interval[0]>0)
    (root/'report.json').write_text(json.dumps(dict(protocol=protocol,summary=summary,runs=rows),indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__': main()
