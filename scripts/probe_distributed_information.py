#!/usr/bin/env python3
"""Balanced engineered information-use fixture, not learning or occupation evidence.

Three explicitly scripted roles isolate one causal path: a carrier observes a
local order, physically returns to a depot and sends it; a supplier chooses cargo
from its own permitted observation; a resident consumes actual delivered input.
Both material kinds and workshop positions are declared before any execution.
Private state changes are confined to artificial tick-zero fixture construction.
"""
import argparse
import hashlib
import json
from pathlib import Path

from distributed_demand_env import ACTIONS, COORDINATES, FEATURES, F, Env, Order, mask


SCHEMA = "hearthbound.distributed-information-mechanism.v0.1"
SEED, HORIZON = 386201, 20
PROTOCOLS = ("local", "unread", "no_messages")
CASES = tuple((node, kind) for node in (1, 2) for kind in (0, 1))


def build_fixture(node, kind, communication):
    """Explicitly replace random initialization BEFORE the first simulation tick."""
    if (node, kind) not in CASES or communication not in PROTOCOLS:
        raise ValueError("Undeclared mechanism fixture")
    run_id = f"mechanism:w{node}:k{kind}:{communication}"
    world = Env(SEED, agents=3, horizon=HORIZON, communication=communication,
                trace=True, run_id=run_id)
    if world.tick != 0:
        raise AssertionError("Fixture setup requires an unstarted world")
    world._initial = 2
    world._depot = [2, 2]
    world._stocks = [[0, 0] for _ in range(3)]
    world._consumed = [0, 0]
    world._schedule = {}
    world._orders = [Order(f"{world._scope}:fixture-order", node, kind, 0, HORIZON, 1)]
    world.initial_nodes = (node, node, 0)
    for citizen, position in zip(world._agents, world.initial_nodes):
        citizen.node = position
        citizen.task = citizen.target = citizen.cargo = citizen.reservation = None
        citizen.remaining = 0
        for memory in (citizen.direct, citizen.reports, citizen.attempted, citizen.last_shared):
            memory.clear()
    for row in [world._counters, *world._per_agent, *world._phases.values()]:
        for key in row:
            row[key] = 0
    world.events.clear()
    world._bump("demand_issued", 1)
    world._emit("FIXTURE_SETUP", scripted_roles={"0": "resident", "1": "carrier", "2": "supplier"},
                initial_nodes=world.initial_nodes, initial_material=[2, 2],
                independent_seed=SEED, random_arrivals_disabled=True)
    world._emit("ORDER_ISSUED", order_id=world._orders[0].order_id, node=node,
                kind=kind, quantity=1, deadline=HORIZON)
    world._refresh_local()
    return world


def supplier_cargo(observation, destination):
    """No true order, shared world, citizen identity or other actor input is read."""
    prefix = f"workshop_{destination}_"
    if observation[F[prefix + "known"]] and observation[F[prefix + "deadline_remaining"]] > 0:
        needs = [observation[F[prefix + "need_" + letter]] for letter in ("a", "b")]
        if max(needs) > 0:
            return int(needs[1] > needs[0])
    return 0  # Declared fixed A fallback; both true material kinds are evaluated.


def fixture_action(citizen, observation, tick, destination):
    """Engineered schedule; only the supplier cargo choice depends on content."""
    valid = mask(observation)
    distance = abs(COORDINATES[destination])
    if citizen == 0:
        return 7 if valid[7] else 0
    if citizen == 1:
        return 1 if tick == 0 else 8 if tick == distance else 0
    if tick == distance + 1:
        return 4 + supplier_cargo(observation, destination)
    if observation[F["cargo_a"]] or observation[F["cargo_b"]]:
        return 6 if valid[6] else destination + 1 if valid[destination + 1] else 0
    return 0


def run_case(node, kind, communication):
    world = build_fixture(node, kind, communication)
    actions_log, rewards, personal = [], 0., [0., 0., 0.]
    decision_tick = abs(COORDINATES[node]) + 1
    pre_choice, choice_observation, cargo_choice = None, None, None
    while not world.done:
        observations = {i: world.obs(i) for i in world.ready()}
        if world.tick == decision_tick:
            metrics = world.metrics()
            pre_choice = dict(personal_rewards=list(personal),
                physics={k: metrics[k] for k in (
                    "depot_A", "depot_B", "workshop_A", "workshop_B", "cargo_A", "cargo_B",
                    "work_in_progress_A", "work_in_progress_B", "produced", "demand_pending",
                    "demand_reserved", "travel_ticks", "attempts")})
            choice_observation = observations[2]
            cargo_choice = supplier_cargo(choice_observation, node)
        actions = {i: fixture_action(i, o, world.tick, node) for i, o in observations.items()}
        actions_log.append(dict(tick=world.tick, actions={str(i): ACTIONS[a] for i, a in actions.items()}))
        colony, own, _ = world.step(actions)
        rewards += colony
        personal = [a + b for a, b in zip(personal, own)]
        metrics = world.metrics()
        if any(metrics[k] != 0 for k in ("conservation_residual_A", "conservation_residual_B", "demand_residual")):
            raise AssertionError("Mechanism fixture violated physical or demand conservation")
    if rewards != metrics["produced"] or choice_observation is None:
        raise AssertionError("Unwitnessed production or missing declared choice")
    return dict(run_id=world.run_id, status="valid", destination=node, required_kind=kind,
        communication=communication, selected_cargo_kind=cargo_choice, decision_tick=decision_tick,
        supplier_observation=choice_observation, pre_choice=pre_choice,
        colony_reward=rewards, personal_reward=personal, metrics=metrics,
        actions=actions_log, events=world.events)


def run_probe():
    rows = []
    for node, kind in CASES:
        for communication in PROTOCOLS:
            try:
                rows.append(run_case(node, kind, communication))
            except Exception as error:
                rows.append(dict(run_id=f"mechanism:w{node}:k{kind}:{communication}", status="failed",
                    destination=node, required_kind=kind, communication=communication,
                    error=f"{type(error).__name__}: {error}", metrics=None))
    valid = [r for r in rows if r["status"] == "valid"]
    source_hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                     for name in ("distributed_demand_env.py", "probe_distributed_information.py")}
    return dict(schema=SCHEMA, source_sha256=source_hashes, seed=SEED, horizon_ticks=HORIZON,
        cases=[dict(destination=n, required_kind=k) for n, k in CASES], protocols=PROTOCOLS,
        observation_features=FEATURES, unknown_material_fallback="A", scripted_roles=True,
        learned_controller=False, emergent_occupation_evidence=False, minecraft_worlds=0,
        interpretation="Constructed paired mechanism demonstration, not independent-world learning evidence",
        planned=12, valid=len(valid), failed=12 - len(valid),
        outputs_by_protocol={p: (sum(r["metrics"]["produced"] for r in valid if r["communication"] == p)
                                if sum(r["communication"] == p for r in valid) == 4 else None) for p in PROTOCOLS},
        runs=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("Refusing to overwrite existing mechanism evidence")
    report = run_probe()
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
        print(json.dumps({k: report[k] for k in ("planned", "valid", "failed", "outputs_by_protocol")}))
    else:
        print(encoded, end="")
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
