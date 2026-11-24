#!/usr/bin/env python3
"""Frozen selective-communication study and recipient-stream interventions.

This is a synthetic research runner. Every planned outcome is retained, including
failed training/evaluation and worlds without a recipient-fork opportunity.
"""
import argparse
import copy
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from recurrent_coordination_policy import Network, SETTINGS, observation_contract, stable_seed, train
from selective_communication_env import ACTIONS, DEMAND_REGIMES, Env, mask, scripted_local


SCHEMA = "hearthbound.selective-coordination-study.v0.1"
VARIANTS = {
    "rnn_local": dict(recurrent=True, communication="local"),
    "mlp_local": dict(recurrent=False, communication="local"),
    "rnn_unread": dict(recurrent=True, communication="unread"),
}


@dataclass(frozen=True)
class Slot:
    name: str
    variant: str = "rnn_local"
    policy: str = "trained"
    communication: str = "local"
    dispatch: str = "selected"
    neural_memory: str = "retained"
    sampling: str = "stochastic"


SLOTS = (
    Slot("rnn_local"),
    Slot("rnn_unread_at_test", communication="unread"),
    Slot("rnn_blocked", communication="no_messages"),
    Slot("rnn_fixed_dispatch", dispatch="fixed"),
    Slot("rnn_neural_reset", neural_memory="reset"),
    Slot("rnn_greedy", sampling="greedy"),
    Slot("rnn_initial", policy="initial"),
    Slot("mlp_local", variant="mlp_local"),
    Slot("mlp_unread_at_test", variant="mlp_local", communication="unread"),
    Slot("mlp_blocked", variant="mlp_local", communication="no_messages"),
    Slot("mlp_fixed_dispatch", variant="mlp_local", dispatch="fixed"),
    Slot("mlp_greedy", variant="mlp_local", sampling="greedy"),
    Slot("mlp_initial", variant="mlp_local", policy="initial"),
    Slot("rnn_trained_unread", variant="rnn_unread", communication="unread"),
    Slot("rnn_trained_unread_readable", variant="rnn_unread"),
    Slot("script_local", variant="baseline", policy="script"),
    Slot("script_unread", variant="baseline", policy="script", communication="unread"),
    Slot("script_blocked", variant="baseline", policy="script", communication="no_messages"),
    Slot("random_local", variant="baseline", policy="random"),
)
FORK_SLOTS = ("rnn_local", "mlp_local")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def source_manifest():
    names = ("distributed_demand_env.py", "selective_communication_env.py",
             "recurrent_coordination_policy.py", "run_selective_coordination.py")
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in names}


def action_uniforms(training_seed, world_seed, horizon, agents):
    """Same indexed uniforms across regimes, policies and paired continuations."""
    return np.random.default_rng(stable_seed("selective-evaluation-actions", training_seed,
                                             world_seed)).random((horizon, agents))


def draw_action(probabilities, uniform, sampling="stochastic"):
    p = np.asarray(probabilities, dtype=float)
    if (p.shape != (len(ACTIONS),) or not np.isfinite(p).all() or np.any(p < 0)
            or not math.isclose(float(p.sum()), 1., abs_tol=1e-10) or not 0 <= uniform < 1):
        raise ValueError("Invalid probability distribution or paired uniform")
    if sampling == "greedy":
        return int(np.argmax(p))
    if sampling != "stochastic":
        raise ValueError("Unknown action sampling rule")
    action = int(np.searchsorted(np.cumsum(p), uniform, side="right"))
    return int(np.flatnonzero(p)[-1]) if action == len(p) else action


def decide(world, model, hidden, slot, uniforms):
    actions, probabilities = {}, {}
    for citizen in world.ready():
        observation = world.actor_obs(citizen)
        available = np.asarray(mask(observation), dtype=bool)
        if slot.policy in ("trained", "initial"):
            previous = model.initial_hidden() if slot.neural_memory == "reset" else hidden[citizen]
            p, hidden[citizen] = model.distribution(observation, previous)
        elif slot.policy == "script":
            p = np.zeros(len(ACTIONS))
            p[scripted_local(observation)] = 1.
        elif slot.policy == "random":
            p = available / available.sum()
        else:
            raise ValueError("Unknown policy")
        action = draw_action(p, uniforms[world.tick, citizen], slot.sampling)
        if not available[action] or np.any(p[~available] != 0):
            raise AssertionError("Policy violated its published local capability mask")
        actions[citizen], probabilities[citizen] = action, p
    return actions, probabilities


def physical_snapshot(world):
    """Evaluator-only audit; private physical state never enters an actor."""
    return dict(tick=world.tick, done=world.done, depot=list(world._depot),
        stocks=copy.deepcopy(world._stocks), consumed=list(world._consumed),
        orders=[(o.node, o.kind, o.issued, o.deadline, o.remaining) for o in world._orders],
        citizens=[dict(node=a.node, travel_cost=a.travel_cost, task=a.task,
                       remaining=a.remaining, target=a.target, cargo=a.cargo,
                       reservation=a.reservation[1:] if a.reservation is not None else None)
                  for a in world._agents])


def verify_metrics(world):
    metrics = world.metrics()
    if any(metrics[k] != 0 for k in ("conservation_residual_A", "conservation_residual_B", "demand_residual")):
        raise AssertionError("Material or work-order conservation failed")
    if (metrics["produced"] != metrics["consumed_A"] + metrics["consumed_B"]
            or metrics["produced"] != sum(p["produced"] for p in metrics["per_agent"])):
        raise AssertionError("Completed production has inconsistent independent ledgers")
    return metrics


def model_fingerprint(model):
    return None if model is None else (model.digest(), model.updates)


def evaluate_trial(model, training_seed, world_seed, demand, slot, *, agents=4, horizon=160,
                   retain_trace=False, capture_recipient=False):
    run_id = f"eval:{training_seed}:{world_seed}:{demand}:{slot.name}"
    world = Env(world_seed, agents=agents, horizon=horizon, demand=demand,
        communication=slot.communication, dispatch_mode=slot.dispatch,
        trace=retain_trace or capture_recipient, run_id=run_id)
    uniforms = action_uniforms(training_seed, world_seed, horizon, agents)
    hidden = [model.initial_hidden() for _ in range(agents)] if model is not None else None
    frozen, captured, action_trace = model_fingerprint(model), None, []
    colony, personal = 0., np.zeros(agents)
    while not world.done:
        actions, probabilities = decide(world, model, hidden, slot, uniforms)
        before = copy.deepcopy(world) if capture_recipient and captured is None and any(
            a >= 8 for a in actions.values()) else None
        after_decision_hidden = copy.deepcopy(hidden) if before is not None else None
        at, event_index = world.tick, len(world.events)
        reward, costs, _ = world.step(actions)
        colony += reward
        personal += costs
        verify_metrics(world)
        if retain_trace:
            action_trace.append(dict(tick=at, actions=actions,
                probabilities={str(i): p.tolist() for i, p in probabilities.items()}))
        if before is not None:
            receipts = [e for e in world.events[event_index:] if e["event"] == "REPORT_DELIVERED"]
            if receipts:
                receipt = min(receipts, key=lambda e: (e["recipient"], e["sender"], e["source_node"]))
                captured = dict(world=before, hidden_after=after_decision_hidden,
                                actions=dict(actions), index_receipt=copy.deepcopy(receipt))
    metrics = verify_metrics(world)
    if (metrics["tick"] != horizon or colony != metrics["produced"]
            or not np.allclose(personal, [a["personal_reward"] for a in metrics["per_agent"]], atol=1e-10)):
        raise AssertionError("Episode horizon or reward ledger mismatch")
    if model_fingerprint(model) != frozen:
        raise AssertionError("Evaluation changed network parameters or optimizer counter")
    row = dict(training_seed=training_seed, world_seed=world_seed, demand=demand,
               slot=slot.name, condition=asdict(slot), run_id=run_id, status="valid",
               colony_reward=colony, personal_reward=personal.tolist(), **metrics)
    example = dict(actions=action_trace, events=world.events) if retain_trace else None
    return row, example, captured


def continue_branch(world, model, hidden, slot, uniforms, recipient, retain_trace=False):
    first, actions_trace = None, []
    while not world.done:
        inspect = first is None and recipient in world.ready()
        if inspect:
            before = dict(tick=world.tick, physical=physical_snapshot(world),
                          hidden=hidden[recipient].tolist(), observation=list(world.actor_obs(recipient)))
        actions, probabilities = decide(world, model, hidden, slot, uniforms)
        if inspect:
            first = dict(before, probabilities=probabilities[recipient].tolist(), action=actions[recipient])
        at = world.tick
        world.step(actions)
        verify_metrics(world)
        if retain_trace:
            actions_trace.append(dict(tick=at, actions=actions,
                probabilities={str(i): p.tolist() for i, p in probabilities.items()}))
    return verify_metrics(world), first, actions_trace


def recipient_fork(model, training_seed, world_seed, demand, slot, baseline_row, captured,
                   *, agents=4, horizon=160, retain_trace=False):
    identity = dict(training_seed=training_seed, world_seed=world_seed, demand=demand,
                    slot=slot.name, fork_id=f"recipient:{training_seed}:{world_seed}:{demand}:{slot.name}")
    if captured is None:
        return dict(identity, status="no_opportunity", reason="No admitted report in the complete baseline world"), None
    frozen = model_fingerprint(model)
    pre, recipient = captured["world"], captured["index_receipt"]["recipient"]
    readable = pre.fork(identity["fork_id"] + ":readable")
    sealed = pre.fork(identity["fork_id"] + ":sealed")
    sealed.set_report_read_suppression([recipient], future_only=True)
    if physical_snapshot(readable) != physical_snapshot(sealed):
        raise AssertionError("Forks differ physically before the index delivery")
    before_metrics = verify_metrics(pre)
    reward_read = readable.step(captured["actions"])
    reward_sealed = sealed.step(captured["actions"])
    if reward_read != reward_sealed or physical_snapshot(readable) != physical_snapshot(sealed):
        raise AssertionError("Content suppression changed the forced index step's physics or costs")
    for branch in (readable, sealed):
        new_receipts = [e for e in branch.events[len(pre.events):]
                        if e["event"] == "REPORT_DELIVERED" and e["recipient"] == recipient]
        fields = ("sender", "recipient", "source_node", "original_observer", "observed_tick",
                  "observation_id", "payload", "parent_message_id")
        expected = tuple(captured["index_receipt"][k] for k in fields)
        if not any(tuple(e[k] for k in fields) == expected for e in new_receipts):
            raise AssertionError("The identical index report was not delivered in both forks")
    uniforms = action_uniforms(training_seed, world_seed, horizon, agents)
    left, first_left, trace_left = continue_branch(readable, model, copy.deepcopy(captured["hidden_after"]),
        slot, uniforms, recipient, retain_trace)
    right, first_right, trace_right = continue_branch(sealed, model, copy.deepcopy(captured["hidden_after"]),
        slot, uniforms, recipient, retain_trace)
    # Prefix evidence has its original scope. Physical behavior must replay the
    # full readable baseline despite the fork's new future event identifiers.
    for key in ("produced", "demand_issued", "demand_expired", "demand_pending", "demand_reserved",
                "attempts", "delivered", "travel_ticks", "work_ticks", "per_agent", "chosen_topics"):
        if left[key] != baseline_row[key]:
            raise AssertionError(f"Readable continuation did not reproduce baseline field {key}")
    if (first_left is None) != (first_right is None):
        raise AssertionError("Recipient decision opportunity differs before any recipient action")
    sensitivity = None
    if first_left is not None:
        if (first_left["tick"] != first_right["tick"] or first_left["physical"] != first_right["physical"]
                or first_left["hidden"] != first_right["hidden"]):
            raise AssertionError("First recipient decision is not paired before policy response")
        p, q = np.asarray(first_left["probabilities"]), np.asarray(first_right["probabilities"])
        sensitivity = dict(tick=first_left["tick"], total_variation=float(np.abs(p - q).sum() / 2),
            sampled_action_changed=first_left["action"] != first_right["action"],
            greedy_action_changed=int(np.argmax(p)) != int(np.argmax(q)),
            readable_action=ACTIONS[first_left["action"]], sealed_action=ACTIONS[first_right["action"]],
            readable_probabilities=p.tolist(), sealed_probabilities=q.tolist())
    recipient_metrics = ("produced", "drops", "pickups", "work_ticks", "travel_ticks", "personal_reward", "shares")
    own = {k: left["per_agent"][recipient][k] - right["per_agent"][recipient][k] for k in recipient_metrics}
    colony_difference = left["produced"] - right["produced"]
    if model_fingerprint(model) != frozen:
        raise AssertionError("Recipient intervention changed the frozen model")
    row = dict(identity, status="valid", recipient=recipient, index_tick=pre.tick,
        index_receipt=captured["index_receipt"], identical_index_physics_and_cost=True,
        readable_continuation_reproduces_baseline=True,
        estimand="Frozen-policy effect of readable report stream from first admitted receipt onward",
        recipient_first_decision=sensitivity,
        readable_colony_suffix_production=left["produced"] - before_metrics["produced"],
        sealed_colony_suffix_production=right["produced"] - before_metrics["produced"],
        colony_production_difference=colony_difference, recipient_differences=own,
        other_citizens_production_difference=colony_difference - own["produced"],
        readable_metrics=left, sealed_metrics=right)
    example = dict(index_actions=captured["actions"],
        readable=dict(actions=trace_left, events=readable.events, first_decision=first_left),
        sealed=dict(actions=trace_right, events=sealed.events, first_decision=first_right)) if retain_trace else None
    return row, example


def crossed_interval(matrix, draws=2000):
    x = np.asarray(matrix, dtype=float)
    if x.ndim != 2 or not x.size or not np.isfinite(x).all():
        raise ValueError("Invalid crossed replicate matrix")
    rng = np.random.default_rng(358)
    seeds = rng.integers(0, x.shape[0], (draws, x.shape[0]))
    worlds = rng.integers(0, x.shape[1], (draws, x.shape[1]))
    samples = x[seeds[:, :, None], worlds[:, None, :]].mean(axis=(1, 2))
    return [float(v) for v in np.quantile(samples, [.025, .975])]


def summarize(rows, forks, seeds, worlds):
    lookup = {}
    for row in rows:
        key = (row["training_seed"], row["world_seed"], row["demand"], row["slot"])
        if key in lookup:
            raise ValueError("Duplicate evaluation slot")
        lookup[key] = row
    planned = len(seeds) * len(worlds)

    def pair(first, second, value=lambda r: r["produced"]):
        matrix = []
        for seed in seeds:
            line = []
            for world in worlds:
                a, b = lookup.get((seed, world, *first)), lookup.get((seed, world, *second))
                if a is None or b is None or a["status"] != "valid" or b["status"] != "valid":
                    return dict(complete=False, mean_difference=None, reason="Missing or failed pairs; no imputation")
                line.append(value(a) - value(b))
            matrix.append(line)
        return dict(complete=True, mean_difference=float(np.mean(matrix)),
            per_training_seed_mean_difference={str(s): float(np.mean(v)) for s, v in zip(seeds, matrix)},
            exploratory_crossed_bootstrap_95_interval=crossed_interval(matrix))

    result = {}
    for demand in DEMAND_REGIMES:
        conditions = {}
        for slot in SLOTS:
            retained = [lookup[(s, w, demand, slot.name)] for s in seeds for w in worlds
                        if (s, w, demand, slot.name) in lookup]
            valid = [r for r in retained if r["status"] == "valid"]
            conditions[slot.name] = dict(planned=planned, retained=len(retained), valid=len(valid),
                failed=len(retained) - len(valid), missing=planned - len(retained),
                mean_products_valid_only=float(np.mean([r["produced"] for r in valid])) if valid else None,
                per_training_seed_mean_products={str(s): float(np.mean([r["produced"] for r in valid
                    if r["training_seed"] == s])) if any(r["training_seed"] == s for r in valid) else None for s in seeds},
                mean_counts_valid_only={k: float(np.mean([r[k] for r in valid])) for k in (
                    "attempts", "delivered", "forwarded", "read_report_inputs", "travel_ticks", "work_ticks",
                    "empty_trips_with_report_delivery", "loaded_trips_with_report_delivery", "demand_expired",
                    "drops_without_current_need") if valid},
                mean_quiet_counts_valid_only={k: float(np.mean([r["phase_counts"]["quiet"][k] for r in valid]))
                    for k in ("produced", "attempts", "travel_ticks", "work_ticks") if valid},
                mean_chosen_topics_valid_only=[float(np.mean([r["chosen_topics"][i] for r in valid]))
                                               for i in range(3)] if valid else None)
        comparisons = {"rnn_minus_" + name: pair((demand, "rnn_local"), (demand, name))
            for name in ("rnn_initial", "mlp_local", "rnn_unread_at_test", "rnn_trained_unread",
                         "rnn_blocked", "rnn_fixed_dispatch", "rnn_neural_reset", "script_local")}
        comparisons["mlp_local_minus_unread"] = pair((demand, "mlp_local"), (demand, "mlp_unread_at_test"))
        result[demand] = dict(conditions=conditions, production_comparisons=comparisons)
    result["shutdown_minus_recurring"] = {name: {field: pair(("shutdown", name), ("recurring", name),
        lambda r, field=field: r["phase_counts"]["quiet"][field])
        for field in ("attempts", "travel_ticks", "produced")} for name in FORK_SLOTS}
    fork_lookup = {}
    for row in forks:
        key = (row["training_seed"], row["world_seed"], row["demand"], row["slot"])
        if key in fork_lookup:
            raise ValueError("Duplicate recipient-fork slot")
        fork_lookup[key] = row
    result["recipient_stream_interventions"] = {}
    for demand in DEMAND_REGIMES:
        for slot in FORK_SLOTS:
            retained = [fork_lookup[(s, w, demand, slot)] for s in seeds for w in worlds
                        if (s, w, demand, slot) in fork_lookup]
            valid = [r for r in retained if r["status"] == "valid"]
            decisions = [r["recipient_first_decision"] for r in valid if r["recipient_first_decision"] is not None]
            entry = dict(planned=planned, retained=len(retained), valid=len(valid),
                no_opportunity=sum(r["status"] == "no_opportunity" for r in retained),
                failed=sum(r["status"] == "failed" for r in retained), missing=planned - len(retained),
                first_decisions=len(decisions),
                conditional_mean_colony_production_difference=float(np.mean([r["colony_production_difference"]
                    for r in valid])) if valid else None,
                conditional_mean_recipient_production_difference=float(np.mean([r["recipient_differences"]["produced"]
                    for r in valid])) if valid else None,
                conditional_mean_other_production_difference=float(np.mean([r["other_citizens_production_difference"]
                    for r in valid])) if valid else None,
                conditional_mean_first_decision_total_variation=float(np.mean([r["total_variation"] for r in decisions]))
                    if decisions else None,
                changed_first_sampled_actions=sum(r["sampled_action_changed"] for r in decisions),
                positive_colony_effect_worlds=sum(r["colony_production_difference"] > 0 for r in valid),
                zero_colony_effect_worlds=sum(r["colony_production_difference"] == 0 for r in valid),
                negative_colony_effect_worlds=sum(r["colony_production_difference"] < 0 for r in valid),
                conditioning="Worlds with a first admitted report; no-opportunity worlds are not zero effects")
            if len(valid) == planned:
                matrix = [[fork_lookup[(s, w, demand, slot)]["colony_production_difference"] for w in worlds] for s in seeds]
                entry["exploratory_crossed_bootstrap_95_interval"] = crossed_interval(matrix)
            result["recipient_stream_interventions"][f"{demand}:{slot}"] = entry
    return result


def train_job(job):
    """A worker owns one seed/variant and its uniquely named checkpoint files."""
    variant, seed, destination, episodes, agents, horizon, frozen_sources = job
    destination = Path(destination)
    name = f"{variant}-{seed}"
    try:
        def progress(entry):
            if entry["episodes_completed"] % 64 == 0 or entry["episodes_completed"] == episodes:
                print(json.dumps(dict(stage="training", variant=variant, **entry), allow_nan=False), flush=True)
        model, initial, stats = train(seed, episodes, agents=agents, horizon=horizon,
            progress=progress, **VARIANTS[variant])
        if source_manifest() != frozen_sources:
            raise AssertionError("Declared source changed during training")
        if not stats["actor_parameter_changed"] or not stats["critic_parameter_changed"] or not model.updates:
            raise AssertionError("Both actor and critic must actually learn")
        model.save(destination / f"trained-{name}.json")
        initial.save(destination / f"initial-{name}.json")
        row = dict(variant=variant, training_seed=seed, status="valid", **stats,
            parameter_sha256=model.digest(), initial_parameter_sha256=initial.digest(),
            actor_parameter_sha256=model.actor_digest(), critic_parameter_sha256=model.critic_digest())
    except Exception as error:
        row = dict(variant=variant, training_seed=seed, status="failed", error=f"{type(error).__name__}: {error}")
    write_json(destination / f"training-{name}.json", row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=512)
    parser.add_argument("--training-seeds", default="17,23,41")
    parser.add_argument("--worlds", type=int, default=12)
    parser.add_argument("--evaluation-seed-start", type=int, default=9600000)
    parser.add_argument("--agents", type=int, default=4)
    parser.add_argument("--horizon", type=int, default=160)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        seeds = [int(s) for s in args.training_seeds.split(",")]
    except ValueError:
        parser.error("Training seeds must be integers")
    if (not 1 <= len(seeds) <= 3 or len(seeds) != len(set(seeds)) or min(seeds) < 0
            or min(args.episodes, args.worlds, args.agents, args.horizon, args.workers) < 1
            or args.workers > 3 or args.evaluation_seed_start < 0):
        parser.error("Use positive dimensions, one to three distinct seeds, and one to three workers")
    worlds = list(range(args.evaluation_seed_start, args.evaluation_seed_start + args.worlds))
    train_worlds = {stable_seed("selective-training-world", s, e) for s in seeds for e in range(args.episodes)}
    if len(train_worlds) != len(seeds) * args.episodes or train_worlds.intersection(worlds):
        raise AssertionError("Training-world collision or held-out contamination")
    destination = args.output_dir
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Output directory is nonempty; prior runs must be retained")
    destination.mkdir(parents=True, exist_ok=True)
    frozen_sources = source_manifest()
    protocol = dict(schema=SCHEMA, base_commit="6c7a341965a438d518c93e30962f7a6cfd2deea5",
        source_manifest=frozen_sources, observation_contract=observation_contract(), settings=SETTINGS,
        variants=VARIANTS, episodes_per_variant_and_training_seed=args.episodes,
        training_seeds=seeds, heldout_world_seeds=worlds, agents=args.agents, horizon_ticks=args.horizon,
        training_worlds_shared_across_variants=True, training_demand="alternating recurring/shutdown",
        parallel_training_workers=args.workers, evaluation_slots=[asdict(s) for s in SLOTS],
        planned_training_runs=len(seeds) * len(VARIANTS),
        planned_evaluation_slots=len(seeds) * len(worlds) * len(DEMAND_REGIMES) * len(SLOTS),
        planned_recipient_forks=len(seeds) * len(worlds) * len(DEMAND_REGIMES) * len(FORK_SLOTS),
        primary_evaluation="stochastic; common uniforms indexed by seed/world/tick/citizen across conditions",
        primary_comparisons=["rnn_local minus equally trained mlp_local", "rnn_local minus rnn_unread_at_test",
            "rnn_local minus equally trained rnn_trained_unread", "quiet shutdown versus recurring activity"],
        recipient_intervention="Pre-first-delivery clone; same index actions/cost/physics; one recipient's future report stream sealed",
        recipient_selection="earliest tick with any admitted report; lowest recipient, then sender, then source node",
        recipient_outcomes=["first-decision distribution total variation", "paired sampled action change",
            "recipient completed production and physical contributions", "colony and other-citizen production"],
        no_opportunity_worlds="retained with unknown effect, not imputed zero",
        neural_reset="only recurrent hidden state; explicit belief memory and previous commands remain",
        fixed_dispatch="frozen-policy protocol intervention; not a separately trained scheduler comparison",
        checkpoint_selection="final declared update only; no held-out selection or stopping",
        independent_units="crossed training and world seeds; citizens/ticks/messages are not replicates",
        uncertainty="exploratory crossed bootstrap; only three training seeds; one common action stream per paired world",
        numpy_version=np.__version__, pilot_only=True, confirmatory_study=False,
        forge_control_enabled=False, minecraft_worlds=0, learned_occupation_established=False)
    write_json(destination / "protocol.json", protocol)
    protocol_hash = hashlib.sha256((destination / "protocol.json").read_bytes()).hexdigest()
    jobs = [(v, s, str(destination), args.episodes, args.agents, args.horizon, frozen_sources)
            for s in seeds for v in VARIANTS]
    training = []
    if args.workers == 1:
        training = [train_job(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(train_job, job): job for job in jobs}
            for future in as_completed(futures):
                job = futures[future]
                try:
                    training.append(future.result())
                except Exception as error:
                    training.append(dict(variant=job[0], training_seed=job[1], status="failed",
                                         error=f"Worker failure: {type(error).__name__}: {error}"))
    training.sort(key=lambda r: (r["training_seed"], r["variant"]))
    write_json(destination / "training.json", training)
    training_lookup = {(r["training_seed"], r["variant"]): r for r in training}
    rows, forks = [], []
    for seed in seeds:
        models = {}
        for variant in VARIANTS:
            record = training_lookup[(seed, variant)]
            if record["status"] == "valid":
                try:
                    models[(variant, "trained")] = Network.load(destination / f"trained-{variant}-{seed}.json")
                    models[(variant, "initial")] = Network.load(destination / f"initial-{variant}-{seed}.json")
                except Exception as error:
                    record.update(status="failed", error=f"Checkpoint load: {type(error).__name__}: {error}")
        examples, fork_examples = {}, {}
        for world_seed in worlds:
            for demand in DEMAND_REGIMES:
                for slot in SLOTS:
                    keep = world_seed == worlds[0]
                    identity = dict(training_seed=seed, world_seed=world_seed, demand=demand,
                        slot=slot.name, condition=asdict(slot),
                        run_id=f"eval:{seed}:{world_seed}:{demand}:{slot.name}")
                    try:
                        model = models.get((slot.variant, slot.policy))
                        if slot.variant != "baseline" and model is None:
                            raise RuntimeError("Required training/checkpoint failed; evaluation not imputed")
                        row, example, capture = evaluate_trial(model, seed, world_seed, demand, slot,
                            agents=args.agents, horizon=args.horizon, retain_trace=keep,
                            capture_recipient=slot.name in FORK_SLOTS)
                        if keep:
                            examples[row["run_id"]] = example
                    except Exception as error:
                        row = dict(identity, status="failed", error=f"{type(error).__name__}: {error}")
                        capture = None
                    rows.append(row)
                    with (destination / "outcomes.jsonl").open("a") as stream:
                        stream.write(json.dumps(row, allow_nan=False) + "\n")
                    if slot.name in FORK_SLOTS:
                        try:
                            if row["status"] != "valid":
                                raise RuntimeError("Baseline failed; recipient opportunity is unknown")
                            fork, fork_example = recipient_fork(model, seed, world_seed, demand, slot, row, capture,
                                agents=args.agents, horizon=args.horizon, retain_trace=keep)
                            if keep and fork_example is not None:
                                fork_examples[fork["fork_id"]] = fork_example
                        except Exception as error:
                            fork = dict(training_seed=seed, world_seed=world_seed, demand=demand, slot=slot.name,
                                fork_id=f"recipient:{seed}:{world_seed}:{demand}:{slot.name}",
                                status="failed", error=f"{type(error).__name__}: {error}")
                        forks.append(fork)
                        with (destination / "recipient-forks.jsonl").open("a") as stream:
                            stream.write(json.dumps(fork, allow_nan=False) + "\n")
        write_json(destination / f"examples-{seed}.json", examples)
        write_json(destination / f"fork-examples-{seed}.json", fork_examples)
        print(json.dumps(dict(stage="evaluated", training_seed=seed,
            retained=len(rows), failed=sum(r["status"] == "failed" for r in rows),
            recipient_forks=len(forks), failed_forks=sum(r["status"] == "failed" for r in forks))), flush=True)
    if source_manifest() != frozen_sources:
        raise AssertionError("Declared source changed during evaluation")
    if len(rows) != protocol["planned_evaluation_slots"] or len(forks) != protocol["planned_recipient_forks"]:
        raise AssertionError("Incomplete planned experiment denominator")
    write_json(destination / "training.json", training)
    report = dict(protocol=protocol, protocol_sha256=protocol_hash, training=training,
        evaluation_weights_frozen=True, summary=summarize(rows, forks, seeds, worlds),
        runs=rows, recipient_forks=forks, forge_control_enabled=False, minecraft_worlds=0,
        learned_occupation_established=False, confirmatory_study=False)
    write_json(destination / "report.json", report)
    print(json.dumps(dict(report=str(destination / "report.json"),
        training_valid=sum(t["status"] == "valid" for t in training),
        outcomes_valid=sum(r["status"] == "valid" for r in rows),
        outcomes_planned=len(rows), recipient_forks_planned=len(forks),
        recipient_forks_valid=sum(r["status"] == "valid" for r in forks),
        recipient_forks_no_opportunity=sum(r["status"] == "no_opportunity" for r in forks),
        recipient_forks_failed=sum(r["status"] == "failed" for r in forks))), flush=True)
    if any(r["status"] == "failed" for r in training + rows + forks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
