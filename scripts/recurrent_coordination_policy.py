#!/usr/bin/env python3
"""Shared recurrent PPO and centralized training critic for synthetic work.

This is a small MAPPO-style adaptation, not a reproduction of a published
benchmark. The actor is an Elman tanh RNN (or a matched feedforward ablation),
not a GRU. It receives only the environment's private actor observation.
Full own-decision sequences are replayed from zero hidden state each PPO epoch.
No message, delivery, specialization, or occupation bonus is provided.
"""
import copy
import hashlib
import math
from pathlib import Path

import numpy as np

from selective_communication_env import ACTIONS, CRITIC_FEATURES, FEATURES
from selective_communication_env import Env, SCHEMA as OBSERVATION_SCHEMA, mask


SCHEMA = "hearthbound.recurrent-coordination-policy.v0.1"
GAMMA, GAE_LAMBDA, PERSONAL_WEIGHT = .98, .95, .25
DEMANDS = ("recurring", "shutdown")
SETTINGS = dict(algorithm="shared-PPO-centralized-critic",
    recurrent_cell="Elman-tanh", actor_hidden_units=32, critic_hidden_units=32,
    actor_adam_rate=.0003, critic_adam_rate=.001, ppo_epochs=4,
    ratio_clip=.2, entropy_coefficient=.01, entropy_final=.0001,
    entropy_schedule="linear across scheduled optimizer batches; initial at first, final at last",
    gradient_norm_clip=.5,
    gamma_per_tick=GAMMA, gae_lambda_per_tick=GAE_LAMBDA,
    personal_reward_weight=PERSONAL_WEIGHT, batch_episodes=8,
    recurrent_training="full own-decision sequence BPTT from zero each epoch",
    advantage_normalization="all decisions in the on-policy world batch",
    value_loss="half mean squared return error", value_clipping=False,
    message_reward=0., delivery_reward=0., occupation_reward=0.)


def stable_seed(*parts):
    return int.from_bytes(hashlib.sha256(repr(parts).encode()).digest()[:8], "big")


def source_manifest():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ("distributed_demand_env.py", "selective_communication_env.py",
                         "recurrent_coordination_policy.py")}


def observation_contract():
    return dict(schema=OBSERVATION_SCHEMA, actor_features=list(FEATURES),
                critic_features=list(CRITIC_FEATURES), actions=list(ACTIONS),
                source_manifest=source_manifest(), critic_used_at_execution=False)


def _digest(parameters):
    digest = hashlib.sha256()
    for name, value in sorted(parameters.items()):
        digest.update(name.encode())
        digest.update(repr(value.shape).encode())
        digest.update(value.astype("<f8").tobytes())
    return digest.hexdigest()


class Network:
    """Shared weights with external, individual hidden state; critic is separate."""

    def __init__(self, seed=0, recurrent=True, hidden=32, critic_hidden=32):
        if type(seed) is not int or seed < 0 or type(recurrent) is not bool:
            raise ValueError("Invalid network seed or architecture")
        if any(type(n) is not int or not 1 <= n <= 256 for n in (hidden, critic_hidden)):
            raise ValueError("Invalid hidden width")
        self.recurrent, self.hidden, self.critic_hidden = recurrent, hidden, critic_hidden
        # Separate streams keep common initial tensors identical across architectures.
        actor_rng = np.random.default_rng(stable_seed("selective-actor", seed))
        critic_rng = np.random.default_rng(stable_seed("selective-critic", seed))
        self.parameters = dict(
            actor_wx=actor_rng.normal(0, 1 / math.sqrt(len(FEATURES)), (len(FEATURES), hidden)),
            actor_bh=np.zeros(hidden),
            actor_wo=actor_rng.normal(0, .01, (hidden, len(ACTIONS))),
            actor_bo=np.zeros(len(ACTIONS)),
            critic_w1=critic_rng.normal(0, 1 / math.sqrt(len(CRITIC_FEATURES)),
                                      (len(CRITIC_FEATURES), critic_hidden)),
            critic_b1=np.zeros(critic_hidden),
            critic_w2=critic_rng.normal(0, .1, (critic_hidden, 1)),
            critic_b2=np.zeros(1))
        if recurrent:
            rng = np.random.default_rng(stable_seed("selective-recurrence", seed))
            orthogonal, _ = np.linalg.qr(rng.normal(size=(hidden, hidden)))
            self.parameters["actor_wh"] = .8 * orthogonal
        self.m = {k: np.zeros_like(v) for k, v in self.parameters.items()}
        self.v = {k: np.zeros_like(v) for k, v in self.parameters.items()}
        self.updates = 0
        self.trainable = True

    def initial_hidden(self):
        return np.zeros(self.hidden)

    def digest(self):
        return _digest(self.parameters)

    def actor_digest(self):
        return _digest({k: v for k, v in self.parameters.items() if k.startswith("actor_")})

    def critic_digest(self):
        return _digest({k: v for k, v in self.parameters.items() if k.startswith("critic_")})

    @staticmethod
    def _masked_probabilities(logits, available):
        logits, available = np.asarray(logits, dtype=float), np.asarray(available, dtype=bool)
        if logits.shape != available.shape or not available.any() or not np.isfinite(logits).all():
            raise ValueError("Invalid masked logits")
        shifted = np.where(available, logits - np.max(logits[available]), -np.inf)
        numerator = np.exp(shifted)
        return numerator / numerator.sum()

    def distribution(self, observation, hidden):
        available = np.asarray(mask(observation), dtype=bool)
        x, old_hidden = np.asarray(observation, dtype=float), np.asarray(hidden, dtype=float)
        if old_hidden.shape != (self.hidden,) or not np.isfinite(old_hidden).all():
            raise ValueError("Invalid individual hidden state")
        p = self.parameters
        z = x @ p["actor_wx"] + p["actor_bh"]
        if self.recurrent:
            z += old_hidden @ p["actor_wh"]
        new_hidden = np.tanh(z)
        probabilities = self._masked_probabilities(
            new_hidden @ p["actor_wo"] + p["actor_bo"], available)
        return probabilities, new_hidden

    def act(self, observation, hidden, rng=None, deterministic=False):
        """Execution needs only local observation, own hidden state, and sampling RNG."""
        if type(deterministic) is not bool:
            raise ValueError("deterministic must be a boolean")
        probabilities, new_hidden = self.distribution(observation, hidden)
        if deterministic:
            action = int(np.argmax(probabilities))
        else:
            if rng is None:
                raise ValueError("Stochastic actions require an explicit sampling RNG")
            draw = float(rng.random())
            if not 0 <= draw < 1:
                raise ValueError("Sampling RNG returned an invalid draw")
            action = int(np.searchsorted(np.cumsum(probabilities), draw, side="right"))
            if action == len(ACTIONS):
                action = int(np.flatnonzero(probabilities)[-1])
        return action, new_hidden, math.log(max(float(probabilities[action]), 1e-300))

    def value(self, critic_input):
        """Training-only value estimate; actor paths never invoke this method."""
        x = np.asarray(critic_input, dtype=float)
        if x.shape != (len(CRITIC_FEATURES),) or not np.isfinite(x).all():
            raise ValueError("Invalid centralized critic input")
        p = self.parameters
        hidden = np.tanh(x @ p["critic_w1"] + p["critic_b1"])
        return float((hidden @ p["critic_w2"] + p["critic_b2"])[0])

    def actor_loss_and_gradients(self, sequences, entropy_coefficient=None):
        """Exact full-sequence BPTT for the masked clipped PPO actor objective."""
        beta = SETTINGS["entropy_coefficient"] if entropy_coefficient is None else entropy_coefficient
        if not math.isfinite(beta) or beta < 0:
            raise ValueError("Invalid entropy coefficient")
        count = sum(len(sequence) for sequence in sequences)
        if not count:
            raise ValueError("Empty actor batch")
        p = self.parameters
        gradients = {k: np.zeros_like(v) for k, v in p.items() if k.startswith("actor_")}
        loss, entropy_total, kl_total, clipped = 0., 0., 0., 0
        for sequence in sequences:
            if not sequence:
                raise ValueError("Empty individual trajectory")
            xs = np.asarray([t["observation"] for t in sequence], dtype=float)
            hs, probabilities, log_probabilities, availabilities = [], [], [], []
            previous = self.initial_hidden()
            for item in sequence:
                available = tuple(mask(item["observation"]))
                if tuple(item["mask"]) != available or not available[item["action"]]:
                    raise ValueError("Trajectory mask/action disagrees with its local observation")
                probs, previous = self.distribution(item["observation"], previous)
                hs.append(previous)
                probabilities.append(probs)
                log_probabilities.append(np.log(np.maximum(probs, 1e-300)))
                availabilities.append(available)
            hs, probabilities = np.asarray(hs), np.asarray(probabilities)
            log_probabilities = np.asarray(log_probabilities)
            available = np.asarray(availabilities, dtype=bool)
            actions = np.asarray([t["action"] for t in sequence], dtype=int)
            old_logps = np.asarray([t["old_log_probability"] for t in sequence])
            advantages = np.asarray([t["normalized_advantage"] for t in sequence])
            selected = log_probabilities[np.arange(len(sequence)), actions]
            differences = selected - old_logps
            ratios = np.exp(differences)
            if not np.isfinite(ratios).all() or not np.isfinite(advantages).all():
                raise ValueError("Nonfinite PPO ratio or advantage")
            low, high = 1 - SETTINGS["ratio_clip"], 1 + SETTINGS["ratio_clip"]
            clipped_ratios = np.clip(ratios, low, high)
            surrogate = np.minimum(ratios * advantages, clipped_ratios * advantages)
            entropy = -(probabilities * log_probabilities).sum(axis=1)
            loss += float((-surrogate - beta * entropy).sum()) / count
            entropy_total += float(entropy.sum())
            kl_total += float(((ratios - 1) - differences).sum())
            clipped += int(np.sum((ratios < low) | (ratios > high)))
            active = ((advantages >= 0) & (ratios <= high)) | ((advantages < 0) & (ratios >= low))
            coefficient = -advantages * ratios * active / count
            dlogits = -coefficient[:, None] * probabilities
            dlogits[np.arange(len(sequence)), actions] += coefficient
            dlogits += beta / count * probabilities * (log_probabilities + entropy[:, None])
            dlogits[~available] = 0.
            gradients["actor_wo"] += hs.T @ dlogits
            gradients["actor_bo"] += dlogits.sum(axis=0)
            direct_dh = dlogits @ p["actor_wo"].T
            dzs = np.zeros_like(hs)
            future_dh = np.zeros(self.hidden)
            for index in range(len(sequence) - 1, -1, -1):
                dzs[index] = (direct_dh[index] + future_dh) * (1 - hs[index] ** 2)
                future_dh = dzs[index] @ p["actor_wh"].T if self.recurrent else np.zeros(self.hidden)
            gradients["actor_wx"] += xs.T @ dzs
            gradients["actor_bh"] += dzs.sum(axis=0)
            if self.recurrent:
                previous_hs = np.vstack((self.initial_hidden(), hs[:-1]))
                gradients["actor_wh"] += previous_hs.T @ dzs
        if not math.isfinite(loss) or not all(np.isfinite(g).all() for g in gradients.values()):
            raise ValueError("Nonfinite actor loss or gradient")
        return loss, gradients, dict(entropy=entropy_total / count,
            approximate_kl=kl_total / count, clip_fraction=clipped / count,
            actor_decisions=count)

    def critic_loss_and_gradients(self, inputs, targets):
        x, targets = np.asarray(inputs, dtype=float), np.asarray(targets, dtype=float)
        if (x.ndim != 2 or x.shape[1] != len(CRITIC_FEATURES) or not len(x)
                or targets.shape != (len(x),) or not np.isfinite(x).all()
                or not np.isfinite(targets).all()):
            raise ValueError("Invalid critic batch")
        p = self.parameters
        hidden = np.tanh(x @ p["critic_w1"] + p["critic_b1"])
        values = (hidden @ p["critic_w2"] + p["critic_b2"]).ravel()
        errors = values - targets
        loss = .5 * float(np.mean(errors ** 2))
        dv = errors[:, None] / len(x)
        dz = (dv @ p["critic_w2"].T) * (1 - hidden ** 2)
        gradients = dict(critic_w1=x.T @ dz, critic_b1=dz.sum(axis=0),
                         critic_w2=hidden.T @ dv, critic_b2=dv.sum(axis=0))
        if not math.isfinite(loss) or not all(np.isfinite(g).all() for g in gradients.values()):
            raise ValueError("Nonfinite critic loss or gradient")
        return loss, gradients

    def update(self, sequences, entropy_coefficient=None):
        """One PPO epoch. Advantages/returns and old log probabilities stay fixed."""
        if not self.trainable:
            raise ValueError("Loaded checkpoints are inference-only; optimizer state was not saved")
        actor_loss, actor_gradients, statistics = self.actor_loss_and_gradients(sequences, entropy_coefficient)
        flat = [item for sequence in sequences for item in sequence]
        critic_loss, critic_gradients = self.critic_loss_and_gradients(
            [t["critic_input"] for t in flat], [t["return"] for t in flat])
        self.updates += 1
        norms = {}
        for kind, gradients, rate in (("actor", actor_gradients, SETTINGS["actor_adam_rate"]),
                ("critic", critic_gradients, SETTINGS["critic_adam_rate"])):
            norm = math.sqrt(sum(float(np.sum(g * g)) for g in gradients.values()))
            if not math.isfinite(norm):
                raise ValueError("Nonfinite gradient norm")
            norms[kind + "_gradient_norm"] = norm
            scale = min(1., SETTINGS["gradient_norm_clip"] / max(norm, 1e-12))
            for name, raw_gradient in gradients.items():
                gradient = raw_gradient * scale
                self.m[name] = .9 * self.m[name] + .1 * gradient
                self.v[name] = .999 * self.v[name] + .001 * gradient * gradient
                corrected_m = self.m[name] / (1 - .9 ** self.updates)
                corrected_v = self.v[name] / (1 - .999 ** self.updates)
                self.parameters[name] -= rate * corrected_m / (np.sqrt(corrected_v) + 1e-8)
        if not all(np.isfinite(p).all() for p in self.parameters.values()):
            raise ValueError("Nonfinite learned parameter")
        return dict(actor_loss=actor_loss, critic_loss=critic_loss,
            entropy_coefficient=SETTINGS["entropy_coefficient"] if entropy_coefficient is None else entropy_coefficient,
            **statistics, **norms)

    def save(self, destination):
        import json
        payload = dict(schema=SCHEMA, observation_contract=observation_contract(),
            recurrent=self.recurrent, hidden_units=self.hidden, critic_hidden_units=self.critic_hidden,
            optimizer_updates=self.updates, inference_only=True, settings=SETTINGS,
            parameter_sha256=self.digest(), actor_parameter_sha256=self.actor_digest(),
            critic_parameter_sha256=self.critic_digest(),
            parameters={k: v.tolist() for k, v in self.parameters.items()})
        Path(destination).write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False) + "\n")

    @classmethod
    def load(cls, source):
        import json
        payload = json.loads(Path(source).read_text())
        if (payload.get("schema") != SCHEMA or payload.get("observation_contract") != observation_contract()
                or payload.get("settings") != SETTINGS or payload.get("inference_only") is not True):
            raise ValueError("Checkpoint observation/action/source/training contract mismatch")
        model = cls(0, recurrent=payload["recurrent"], hidden=payload["hidden_units"],
                    critic_hidden=payload["critic_hidden_units"])
        parameters = {k: np.asarray(v, dtype=float) for k, v in payload["parameters"].items()}
        if (set(parameters) != set(model.parameters) or any(
                parameters[k].shape != model.parameters[k].shape or not np.isfinite(parameters[k]).all()
                for k in parameters)):
            raise ValueError("Invalid checkpoint tensor keys, shapes, or values")
        if type(payload["optimizer_updates"]) is not int or payload["optimizer_updates"] < 0:
            raise ValueError("Invalid checkpoint update count")
        model.parameters, model.updates = parameters, payload["optimizer_updates"]
        if (model.digest() != payload.get("parameter_sha256")
                or model.actor_digest() != payload.get("actor_parameter_sha256")
                or model.critic_digest() != payload.get("critic_parameter_sha256")):
            raise ValueError("Checkpoint parameter digest mismatch")
        model.trainable = False
        return model


def generalized_advantages(sequence):
    """Duration-correct SMDP GAE, with no value beyond a terminal world."""
    if not sequence or sequence[-1]["terminal"] is not True:
        raise ValueError("A complete individual sequence must finish at the episode boundary")
    next_advantage, next_value = 0., 0.
    for index in range(len(sequence) - 1, -1, -1):
        item = sequence[index]
        duration = item["duration"]
        if type(duration) is not int or duration < 1 or type(item["terminal"]) is not bool:
            raise ValueError("Invalid duration or terminal flag")
        if item["terminal"] and index != len(sequence) - 1:
            raise ValueError("Individual trajectory continues after termination")
        continuation = not item["terminal"]
        delta = item["discounted_reward"] + GAMMA ** duration * next_value * continuation - item["value"]
        advantage = delta + (GAMMA * GAE_LAMBDA) ** duration * next_advantage * continuation
        if not math.isfinite(advantage):
            raise ValueError("Nonfinite generalized advantage")
        item["advantage"], item["return"] = float(advantage), float(advantage + item["value"])
        next_advantage, next_value = advantage, item["value"]


def prepare_batch(sequences):
    for sequence in sequences:
        generalized_advantages(sequence)
    flat = [item for sequence in sequences for item in sequence]
    if not flat:
        raise ValueError("Empty on-policy batch")
    advantages = np.asarray([item["advantage"] for item in flat])
    center, scale = float(advantages.mean()), float(advantages.std()) + 1e-8
    for item in flat:
        item["normalized_advantage"] = (item["advantage"] - center) / scale
    return dict(decisions=len(flat), advantage_mean=center, advantage_standard_deviation=scale - 1e-8)


def collect_episode(model, world, rng, *, deterministic=False, training=True, trace=False,
                    reset_memory_each_decision=False):
    """Collect complete asynchronous trajectories with every actor tick accounted for.

    With training=False the centralized critic is never queried. Execution and
    evaluation can also call Network.act directly without this collector.
    """
    hidden = [model.initial_hidden() for _ in range(world.agents)]
    sequences, pending = [[] for _ in range(world.agents)], {}
    colony_total, personal_total, action_trace = 0., [0.] * world.agents, []
    halves = [dict(produced=0., personal_cost=0., action_counts={a: 0 for a in ACTIONS}) for _ in range(2)]

    def finish(agent, terminal):
        item = pending.pop(agent)
        item["terminal"] = bool(terminal)
        if item["duration"] < 1:
            raise AssertionError("A decision transition has no elapsed ticks")
        sequences[agent].append(item)

    while not world.done:
        half = int(world.tick >= world.horizon // 2)
        actions = {}
        for agent in world.ready():
            if agent in pending:
                finish(agent, False)
            observation = tuple(world.actor_obs(agent))
            previous_hidden = model.initial_hidden() if reset_memory_each_decision else hidden[agent]
            action, hidden[agent], logp = model.act(observation, previous_hidden, rng, deterministic)
            actions[agent] = action
            critic_input = tuple(world.critic_state(agent)) if training else None
            pending[agent] = dict(agent=agent, start_tick=world.tick,
                observation=observation, mask=tuple(mask(observation)), action=action,
                old_log_probability=logp, critic_input=critic_input,
                value=model.value(critic_input) if training else 0.,
                duration=0, discounted_reward=0., personal_reward=0., colony_reward=0.)
            halves[half]["action_counts"][ACTIONS[action]] += 1
            if trace:
                action_trace.append(dict(tick=world.tick, citizen=agent, action=ACTIONS[action],
                    observation=observation, hidden_before=previous_hidden.tolist(),
                    hidden_after=hidden[agent].tolist(), log_probability=logp))
        colony, personal, done = world.step(actions)
        if (len(personal) != world.agents or not math.isfinite(colony)
                or not all(map(math.isfinite, personal)) or set(pending) != set(range(world.agents))):
            raise AssertionError("Invalid reward ledger or missing actor transition")
        colony_total += colony
        halves[half]["produced"] += colony
        halves[half]["personal_cost"] -= sum(personal)
        for agent, item in pending.items():
            item["discounted_reward"] += GAMMA ** item["duration"] * (colony + PERSONAL_WEIGHT * personal[agent])
            item["duration"] += 1
            item["personal_reward"] += personal[agent]
            item["colony_reward"] += colony
            personal_total[agent] += personal[agent]
        if done:
            for agent in list(pending):
                finish(agent, True)
    for agent, sequence in enumerate(sequences):
        if (sum(t["duration"] for t in sequence) != world.horizon
                or [t["start_tick"] for t in sequence] != list(np.cumsum(
                    [0] + [t["duration"] for t in sequence[:-1]]))
                or not math.isclose(sum(t["personal_reward"] for t in sequence), personal_total[agent], abs_tol=1e-10)
                or sum(t["colony_reward"] for t in sequence) != colony_total):
            raise AssertionError("Missing, overlapping, or miscredited actor ticks")
    metrics = world.metrics()
    if (metrics["produced"] != colony_total or any(metrics[k] != 0 for k in (
            "conservation_residual_A", "conservation_residual_B", "demand_residual"))):
        raise AssertionError("Production reward, material, or demand accounting failed")
    metrics.update(personal_reward=personal_total, colony_reward=colony_total,
        policy_decisions=sum(len(s) for s in sequences), activity_by_half=halves)
    if trace:
        metrics.update(action_trace=action_trace, world_events=copy.deepcopy(world.events))
    return metrics, sequences


def train(seed, episodes, *, recurrent=True, communication="local", batch_episodes=8,
          agents=4, horizon=160, progress=None):
    """Freeze each batch's behavior policy while collecting complete world episodes."""
    if (type(seed) is not int or seed < 0 or type(recurrent) is not bool
            or communication not in ("local", "unread")
            or any(type(x) is not int or x < 1 for x in (episodes, batch_episodes, agents, horizon))):
        raise ValueError("Invalid training configuration")
    model = Network(seed, recurrent=recurrent)
    initial = copy.deepcopy(model)
    frozen_sources = source_manifest()
    world_digest = hashlib.sha256()
    by_demand = {d: dict(episodes=0, products=0) for d in DEMANDS}
    losses, batch_summaries, products, decisions = [], [], 0, 0
    for batch_start in range(0, episodes, batch_episodes):
        sequences = []
        behavior_digest = model.digest()
        for episode in range(batch_start, min(episodes, batch_start + batch_episodes)):
            demand = DEMANDS[episode % len(DEMANDS)]
            world_seed = stable_seed("selective-training-world", seed, episode)
            world_digest.update(f"{world_seed}:{demand}\n".encode())
            rng = np.random.default_rng(stable_seed("selective-training-actions", seed, episode))
            world = Env(world_seed, agents=agents, horizon=horizon, communication=communication, demand=demand,
                run_id=f"train:{'rnn' if recurrent else 'mlp'}:{communication}:{seed}:{episode}:{demand}")
            metrics, own_sequences = collect_episode(model, world, rng)
            sequences.extend(own_sequences)
            products += metrics["produced"]
            decisions += metrics["policy_decisions"]
            by_demand[demand]["episodes"] += 1
            by_demand[demand]["products"] += metrics["produced"]
        if behavior_digest != model.digest():
            raise AssertionError("On-policy batch collection changed network weights")
        batches = math.ceil(episodes / batch_episodes)
        fraction = (batch_start // batch_episodes) / max(1, batches - 1)
        entropy_coefficient = (SETTINGS["entropy_coefficient"]
            + fraction * (SETTINGS["entropy_final"] - SETTINGS["entropy_coefficient"]))
        summary = prepare_batch(sequences)
        summary.update(first_episode=batch_start, episodes=len(sequences) // agents,
                       behavior_parameter_sha256=behavior_digest, entropy_coefficient=entropy_coefficient)
        for _ in range(SETTINGS["ppo_epochs"]):
            losses.append(model.update(sequences, entropy_coefficient))
        batch_summaries.append(summary)
        if source_manifest() != frozen_sources:
            raise AssertionError("Source changed during the declared training run")
        completed = min(episodes, batch_start + batch_episodes)
        if progress:
            progress(dict(architecture="recurrent" if recurrent else "feedforward", training_seed=seed,
                training_communication=communication, entropy_coefficient=entropy_coefficient,
                episodes_completed=completed, optimizer_updates=model.updates, training_products=products,
                actor_loss=losses[-1]["actor_loss"], critic_loss=losses[-1]["critic_loss"],
                entropy=losses[-1]["entropy"], approximate_kl=losses[-1]["approximate_kl"]))
    statistics = dict(architecture="recurrent" if recurrent else "feedforward", episodes=episodes,
        training_communication=communication,
        batch_episodes=batch_episodes, world_ticks=episodes * horizon, agent_ticks=episodes * horizon * agents,
        decisions=decisions, training_products=products, optimizer_updates=model.updates,
        actor_parameter_changed=model.actor_digest() != initial.actor_digest(),
        critic_parameter_changed=model.critic_digest() != initial.critic_digest(),
        source_manifest=frozen_sources, training_world_seed_manifest_sha256=world_digest.hexdigest(),
        by_demand=by_demand, batch_records=batch_summaries,
        mean_epoch_statistics={key: float(np.mean([entry[key] for entry in losses])) for key in losses[0]},
        last_epoch_statistics=losses[-1])
    return model, initial, statistics
