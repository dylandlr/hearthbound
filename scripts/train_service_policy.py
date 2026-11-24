#!/usr/bin/env python3
"""Shared candidate Double-DQN for private sustained service menus (v0.22).

Experience is pooled OFFLINE. The exported Minecraft actor is frozen. This is
independent Q-learning with shared parameters, not MAPPO or a centralized critic.
"""
import argparse
from collections import deque
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import numpy as np
from service_option_env import SCHEMA, GAMMA, PERSONAL_WEIGHT, Env, episode, authored, encode, features, KINDS

SHAPES = dict(w1=(30, 32), b1=(32,), w2=(32, 16), b2=(16,), w3=(16, 1), b3=(1,))
HEADER = f'HEARTHBOUND_SERVICE_DDQN_V1 {SCHEMA} 30 32 16 1'
PROTOCOL = dict(schema='hearthbound.shared-service-learning.v0.22', training_seeds=[11, 29, 47],
                deployed_seed=11, episodes=500, horizon_seconds=120, evaluation_worlds=list(range(22000, 22024)),
                gamma_per_second=GAMMA, personal_weight=PERSONAL_WEIGHT, colony_weight=1-PERSONAL_WEIGHT,
                research_reward=0, batch_size=32, replay_capacity=20000, target_update_interval=200,
                learning_rate=.0005, epsilon_start=.9, epsilon_end=.05, updates_per_second=1,
                topology='30-32-ReLU-16-ReLU-1', tie_break='lexicographic candidate id',
                actor_input=SCHEMA, live_weight_updates=0, receipt_origin='SYNTHETIC')


class Network:
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        self.p = {k: (rng.normal(0, math.sqrt(2 / shape[0]) if k != 'w3' else .03, shape)
                      if k.startswith('w') else np.zeros(shape)) for k, shape in SHAPES.items()}
        self.m = {k: np.zeros_like(v) for k, v in self.p.items()}; self.v = copy.deepcopy(self.m); self.updates = 0

    def values(self, x):
        p = self.p
        return (np.maximum(np.maximum(np.asarray(x) @ p['w1'] + p['b1'], 0) @ p['w2'] + p['b2'], 0)
                @ p['w3'] + p['b3']).reshape(-1)

    def targets(self, batch, target):
        successors = np.concatenate([t['next'] for t in batch]); q = self.values(successors); tq = target.values(successors)
        expected = []; offset = 0
        for t in batch:
            n = len(t['next']); best = offset + int(np.argmax(q[offset:offset+n])); offset += n
            if type(t['duration']) is not int or t['duration'] < 1: raise ValueError('Invalid duration')
            expected.append(t['reward'] + (0. if t['terminal'] else GAMMA ** t['duration'] * tq[best]))
        return np.asarray(expected)

    def loss_gradients(self, x, expected):
        p = self.p; x = np.asarray(x); expected = np.asarray(expected)
        z1 = x @ p['w1'] + p['b1']; h1 = np.maximum(z1, 0)
        z2 = h1 @ p['w2'] + p['b2']; h2 = np.maximum(z2, 0)
        error = (h2 @ p['w3'] + p['b3']).reshape(-1) - expected
        loss = float(np.where(abs(error) <= 1, .5 * error**2, abs(error)-.5).mean())
        dq = np.clip(error, -1, 1)[:, None] / len(x); d2 = (dq @ p['w3'].T) * (z2 > 0)
        d1 = (d2 @ p['w2'].T) * (z1 > 0)
        return loss, dict(w3=h2.T @ dq, b3=dq.sum(axis=0), w2=h1.T @ d2, b2=d2.sum(axis=0),
                          w1=x.T @ d1, b1=d1.sum(axis=0))

    def update(self, batch, target):
        loss, gradients = self.loss_gradients([t['x'] for t in batch], self.targets(batch, target))
        norm = math.sqrt(sum(float((g*g).sum()) for g in gradients.values())); self.updates += 1
        if not math.isfinite(norm + loss): raise ValueError('Nonfinite gradient')
        for k, g in gradients.items():
            g = g * min(1., 5. / max(norm, 1e-12)); self.m[k] = .9*self.m[k]+.1*g; self.v[k] = .999*self.v[k]+.001*g*g
            self.p[k] -= PROTOCOL['learning_rate'] * (self.m[k]/(1-.9**self.updates)) / (np.sqrt(self.v[k]/(1-.999**self.updates))+1e-8)
        return loss

    def bundle(self):
        return (HEADER+'\n'+'\n'.join(k+' '+' '.join(format(float(v), '.17g') for v in self.p[k].flat) for k in SHAPES)+'\n').encode()

    def digest(self): return hashlib.sha256(self.bundle()).hexdigest()

    def save(self, path):
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(self.bundle())
        path.with_suffix(path.suffix+'.sha256').write_text(self.digest()+'\n')

    @classmethod
    def load(cls, path):
        raw = Path(path).read_bytes(); expected = Path(str(path)+'.sha256').read_text().strip()
        if hashlib.sha256(raw).hexdigest() != expected: raise ValueError('Checkpoint hash mismatch')
        lines = raw.decode('ascii').splitlines()
        if lines[0] != HEADER or len(lines) != 7: raise ValueError('Checkpoint schema mismatch')
        model = cls(0)
        for line, (name, shape) in zip(lines[1:], SHAPES.items()):
            tokens = line.split()
            if tokens[0] != name or len(tokens) != 1 + math.prod(shape): raise ValueError('Checkpoint shape mismatch')
            x = np.asarray([float(t) for t in tokens[1:]]).reshape(shape)
            if not np.isfinite(x).all() or np.any(abs(x) > 1000): raise ValueError('Invalid checkpoint tensor')
            model.p[name] = x
        return model


def train(seed, episodes, folder):
    model = Network(seed); model.save(folder/f'untrained-{seed}.txt'); target = copy.deepcopy(model)
    rng = random.Random(seed); replay = deque(maxlen=20000); history = []; losses = []
    for e in range(episodes):
        epsilon = .9 + (.05-.9) * min(1., e/(episodes*.8))
        def policy(menu, x): return rng.randrange(len(menu)) if rng.random() < epsilon else int(np.argmax(model.values(x)))
        def update():
            if len(replay) < 64: return
            losses.append(model.update(rng.sample(list(replay), 32), target))
            if model.updates % 200 == 0: target.p = copy.deepcopy(model.p)
        result = episode(Env(seed*100000+e), policy, replay.append, update)
        history.append(dict(episode=e, output=result['output'], costs=sum(result['costs']), failures=result['executor_refusals']))
        if (e+1) % 100 == 0: print(json.dumps(dict(seed=seed, episode=e+1, updates=model.updates, mean_output_last100=np.mean([h['output'] for h in history[-100:]]))), flush=True)
    model.save(folder/f'trained-{seed}.txt')
    return dict(seed=seed, updates=model.updates, model_sha256=model.digest(), initial_sha256=Network(seed).digest(),
                final_loss_mean=float(np.mean(losses[-100:])), history=history)


def evaluate(folder, worlds, seeds):
    results = []
    for seed in seeds:
        for arm in ('trained', 'untrained', 'authored'):
            model = Network.load(folder/f'{arm if arm != "authored" else "untrained"}-{seed}.txt'); before=model.digest()
            for world in worlds:
                result = episode(Env(world), lambda menu, x: authored(menu) if arm == 'authored' else int(np.argmax(model.values(x))))
                results.append(dict(training_seed=seed, arm=arm, model_sha256=None if arm=='authored' else before, **result))
            if model.digest() != before: raise AssertionError('Evaluation changed weights')
    return results


def parity(folder, model):
    cases = []
    for world in (31, 47, 59):
        env = Env(world)
        for a in env.ready():
            menu=env.menu(a); x=encode(menu)
            for row, value in zip(x, model.values(x)): cases.append([*map(float, row), float(value)])
    # Include all action kinds, remote claim ages, wide menus and saturation edges.
    menu = [dict(features=features(k, 64, 90, 600, .75)) for k in KINDS]
    for row, value in zip(encode(menu), model.values(encode(menu))): cases.append([*map(float, row), float(value)])
    (folder/'parity.tsv').write_text('\n'.join('\t'.join(format(v,'.17g') for v in row) for row in cases)+'\n')


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--episodes',type=int,default=500); parser.add_argument('--seeds',type=int,nargs='+',default=[11,29,47]); parser.add_argument('--development',action='store_true')
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    if not args.development and (args.episodes != 500 or args.seeds != [11,29,47]): raise ValueError('Confirmatory protocol is frozen')
    source_hashes={n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in ('service_option_env.py','train_service_policy.py')}
    protocol=dict(PROTOCOL, development=args.development, actual_episodes=args.episodes, actual_training_seeds=args.seeds, sources=source_hashes, numpy=np.__version__)
    (args.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    histories=[train(s,args.episodes,args.output) for s in args.seeds]
    worlds=list(range(21000,21008)) if args.development else PROTOCOL['evaluation_worlds']
    results=evaluate(args.output,worlds,args.seeds)
    (args.output/'results.json').write_text(json.dumps(dict(protocol=protocol,training=histories,evaluation=results),indent=2)+'\n')
    parity(args.output,Network.load(args.output/f'trained-{args.seeds[0]}.txt'))
    for arm in ('trained','untrained','authored'):
        values=[r['output'] for r in results if r['arm']==arm]
        print(json.dumps(dict(arm=arm, worlds=len(values), mean_output=float(np.mean(values)), minimum=min(values), maximum=max(values))),flush=True)

if __name__=='__main__': main()
