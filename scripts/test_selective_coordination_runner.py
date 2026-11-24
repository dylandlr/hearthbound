import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from recurrent_coordination_policy import Network
import run_selective_coordination as runner
from selective_communication_env import ACTIONS, Env, F, mask


TRAINING_SEED, WORLD_SEED = 101, 73031


def physical_fixture(seed, **kwargs):
    """Prescribed placement; the report is witnessed and physically carried."""
    world = Env(seed, **kwargs)
    for i, actor in enumerate(world._agents):
        actor.node = 2 if i == 0 else 0
        actor.direct.clear()
        actor.reports.clear()
    world._refresh_local()
    return world


def fixture_uniforms(training_seed, world_seed, horizon, agents):
    """A declared unit-test action stream, not a learned-success experiment."""
    uniforms = np.zeros((horizon, agents))
    uniforms[0, 0] = .5
    if horizon > 4:
        uniforms[4, 0] = np.nextafter(1., 0.)
    return uniforms


def fork_fixture():
    model = Network(TRAINING_SEED)
    slot = runner.SLOTS[0]
    with patch.object(runner, "Env", side_effect=physical_fixture), patch.object(
            runner, "action_uniforms", side_effect=fixture_uniforms):
        baseline, example, capture = runner.evaluate_trial(model, TRAINING_SEED, WORLD_SEED,
            "recurring", slot, horizon=40, retain_trace=True, capture_recipient=True)
        fork, fork_example = runner.recipient_fork(model, TRAINING_SEED, WORLD_SEED,
            "recurring", slot, baseline, capture, horizon=40, retain_trace=True)
    return model, baseline, example, capture, fork, fork_example


def stub_training(seed, episodes, *, recurrent=True, **kwargs):
    """Only for CLI error-handling tests; no training-quality claim is made."""
    initial = Network(seed, recurrent=recurrent)
    model = copy.deepcopy(initial)
    model.parameters["actor_bo"][0] += 1e-4
    model.parameters["critic_b2"][0] += 1e-4
    model.updates = 1
    return model, initial, dict(actor_parameter_changed=True, critic_parameter_changed=True,
                               episodes=episodes, unit_test_stub=True)


class SelectiveRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = fork_fixture()

    def test_action_uniforms_are_indexed_and_repeatable(self):
        first = runner.action_uniforms(TRAINING_SEED, WORLD_SEED, 40, 4)
        repeated = runner.action_uniforms(TRAINING_SEED, WORLD_SEED, 40, 4)
        extended = runner.action_uniforms(TRAINING_SEED, WORLD_SEED, 80, 4)
        np.testing.assert_array_equal(first, repeated)
        np.testing.assert_array_equal(first, extended[:40])
        for tick, citizen in ((0, 3), (27, 1), (2, 0), (39, 2)):
            self.assertEqual(first[tick, citizen], repeated[tick, citizen])
        self.assertFalse(np.array_equal(first,
            runner.action_uniforms(TRAINING_SEED + 1, WORLD_SEED, 40, 4)))
        self.assertFalse(np.array_equal(first,
            runner.action_uniforms(TRAINING_SEED, WORLD_SEED + 1, 40, 4)))
        self.assertTrue(np.all((first >= 0) & (first < 1)))

    def test_draw_action_skips_zero_probability_and_checks_inputs(self):
        probabilities = np.zeros(len(ACTIONS))
        probabilities[[0, 3, 10]] = [.2, .3, .5]
        for uniform, expected in ((0., 0), (.2, 3), (.499, 3), (.5, 10), (np.nextafter(1., 0.), 10)):
            self.assertEqual(runner.draw_action(probabilities, uniform), expected)
        self.assertEqual(runner.draw_action(probabilities, 0., "greedy"), 10)
        for p, u in ((probabilities[:-1], .3), (probabilities * .5, .3),
                     (probabilities, 1.), (probabilities, float("nan"))):
            with self.assertRaises(ValueError):
                runner.draw_action(p, u)
        with self.assertRaises(ValueError):
            runner.draw_action(probabilities, .1, "unknown")

    def test_all_policy_paths_obey_the_same_local_masks(self):
        model = Network(TRAINING_SEED)
        for policy in ("trained", "script", "random"):
            world = Env(WORLD_SEED, horizon=24)
            slot = runner.Slot("unit-" + policy, policy=policy)
            hidden = [model.initial_hidden() for _ in range(world.agents)]
            uniforms = runner.action_uniforms(TRAINING_SEED, WORLD_SEED, 24, world.agents)
            while not world.done:
                available = {i: np.asarray(mask(world.actor_obs(i))) for i in world.ready()}
                actions, probabilities = runner.decide(world, model, hidden, slot, uniforms)
                self.assertEqual(set(actions), set(world.ready()))
                for i, action in actions.items():
                    self.assertTrue(available[i][action])
                    self.assertTrue(np.all(probabilities[i][~available[i]] == 0))
                    self.assertAlmostEqual(float(probabilities[i].sum()), 1.)
                world.step(actions)

    def test_evaluation_never_queries_critic_and_keeps_weights_frozen(self):
        model = Network(TRAINING_SEED)
        before = runner.model_fingerprint(model)
        with patch.object(model, "value", side_effect=AssertionError("Critic used during execution")), patch.object(
                Env, "critic_state", side_effect=AssertionError("Global critic input used during execution")):
            row, _, _ = runner.evaluate_trial(model, TRAINING_SEED, WORLD_SEED, "recurring",
                runner.SLOTS[0], horizon=40)
        self.assertEqual(row["status"], "valid")
        self.assertEqual(row["tick"], 40)
        self.assertEqual(runner.model_fingerprint(model), before)

    def test_pre_receipt_fork_preserves_physics_and_replays_readable_baseline(self):
        model, baseline, example, capture, fork, trace = self.fixture
        self.assertIsNotNone(capture)
        self.assertEqual(capture["world"].tick, 4)
        self.assertEqual(capture["index_receipt"]["tick"], 4)
        self.assertEqual(capture["index_receipt"]["source_node"], 2)
        self.assertEqual(fork["status"], "valid")
        self.assertTrue(fork["identical_index_physics_and_cost"])
        self.assertTrue(fork["readable_continuation_reproduces_baseline"])
        self.assertEqual(fork["readable_metrics"]["per_agent"], baseline["per_agent"])
        self.assertEqual(fork["readable_metrics"]["chosen_topics"], baseline["chosen_topics"])
        for side in ("readable_metrics", "sealed_metrics"):
            self.assertEqual(fork[side]["conservation_residual_A"], 0)
            self.assertEqual(fork[side]["conservation_residual_B"], 0)
            self.assertEqual(fork[side]["demand_residual"], 0)
        self.assertEqual(fork["colony_production_difference"],
            fork["recipient_differences"]["produced"] + fork["other_citizens_production_difference"])

    def test_first_recipient_decision_is_paired_before_any_response(self):
        _, _, _, capture, fork, trace = self.fixture
        left, right = trace["readable"]["first_decision"], trace["sealed"]["first_decision"]
        self.assertEqual(left["tick"], right["tick"])
        self.assertEqual(left["tick"], capture["world"].tick + 1)
        self.assertEqual(left["physical"], right["physical"])
        self.assertEqual(left["hidden"], right["hidden"])
        self.assertEqual(left["observation"][F["workshop_2_known"]], 1)
        self.assertEqual(right["observation"][F["workshop_2_known"]], 0)
        p, q = np.asarray(left["probabilities"]), np.asarray(right["probabilities"])
        self.assertAlmostEqual(fork["recipient_first_decision"]["total_variation"], float(np.abs(p - q).sum() / 2))
        for decision in (left, right):
            available = np.asarray(mask(decision["observation"]))
            self.assertTrue(np.all(np.asarray(decision["probabilities"])[~available] == 0))
        sealed_events = trace["sealed"]["events"]
        intervention_index = next(i for i, e in enumerate(sealed_events) if e["event"] == "REPORT_READ_INTERVENTION")
        index_delivery = next(i for i, e in enumerate(sealed_events) if e["event"] == "REPORT_DELIVERED"
                              and e["recipient"] == fork["recipient"])
        self.assertLess(intervention_index, index_delivery)
        self.assertIn("stream", fork["estimand"])

    def test_new_order_ids_do_not_break_fork_physical_pairing(self):
        model = Network(TRAINING_SEED)
        world = physical_fixture(WORLD_SEED, horizon=40, trace=True, run_id="arrival-regression")
        world._agents[0].node = 0
        world._agents[0].direct.clear()
        world._refresh_local()
        world.step({i: 3 if i == 0 else 0 for i in world.ready()})
        while 0 not in world.ready():
            world.step({i: 0 for i in world.ready()})
        world.step({i: 1 if i == 0 else 0 for i in world.ready()})
        while world.tick < 27:
            world.step({i: 0 for i in world.ready()})
        self.assertTrue(mask(world.actor_obs(0))[10])
        hidden = [model.initial_hidden() for _ in range(world.agents)]
        uniforms = np.zeros((40, world.agents))
        uniforms[27, 0] = np.nextafter(1., 0.)
        actions, _ = runner.decide(world, model, hidden, runner.SLOTS[0], uniforms)
        self.assertEqual(actions[0], 10)
        before = copy.deepcopy(world)
        index = len(world.events)
        world.step(actions)
        receipt = next(e for e in world.events[index:] if e["event"] == "REPORT_DELIVERED")
        capture = dict(world=before, hidden_after=copy.deepcopy(hidden), actions=actions, index_receipt=receipt)
        baseline, _, _ = runner.continue_branch(world, model, copy.deepcopy(hidden), runner.SLOTS[0],
                                                uniforms, receipt["recipient"])
        with patch.object(runner, "action_uniforms", return_value=uniforms):
            fork, trace = runner.recipient_fork(model, TRAINING_SEED, WORLD_SEED, "recurring",
                runner.SLOTS[0], baseline, capture, horizon=40, retain_trace=True)
        self.assertEqual(fork["status"], "valid")
        self.assertEqual(fork["recipient_first_decision"]["tick"], 28)
        self.assertEqual(trace["readable"]["first_decision"]["physical"],
                         trace["sealed"]["first_decision"]["physical"])
        ids = [[e["order_id"] for e in trace[branch]["events"]
                if e["event"] == "ORDER_ISSUED" and e["tick"] == 28] for branch in ("readable", "sealed")]
        self.assertEqual(len(ids[0]), 2)
        self.assertNotEqual(ids[0], ids[1])

    def test_no_delivery_opportunity_remains_unknown(self):
        model = Network(TRAINING_SEED)
        baseline, _, capture = runner.evaluate_trial(model, TRAINING_SEED, WORLD_SEED,
            "recurring", runner.SLOTS[0], horizon=1, capture_recipient=True)
        self.assertIsNone(capture)
        row, trace = runner.recipient_fork(model, TRAINING_SEED, WORLD_SEED, "recurring",
            runner.SLOTS[0], baseline, capture, horizon=1)
        self.assertEqual(row["status"], "no_opportunity")
        self.assertNotIn("colony_production_difference", row)
        self.assertIsNone(trace)
        summary = runner.summarize([], [row], [TRAINING_SEED], [WORLD_SEED])
        entry = summary["recipient_stream_interventions"]["recurring:rnn_local"]
        self.assertEqual((entry["planned"], entry["no_opportunity"], entry["valid"]), (1, 1, 0))
        self.assertIsNone(entry["conditional_mean_colony_production_difference"])

    def test_failed_and_missing_pairs_are_not_imputed(self):
        _, baseline, _, _, _, _ = self.fixture
        worlds = [WORLD_SEED, WORLD_SEED + 1]
        rows = [dict(copy.deepcopy(baseline), world_seed=w, slot=slot,
                     produced=5 if slot == "rnn_local" else 3)
                for w in worlds for slot in ("rnn_local", "rnn_unread_at_test")]
        complete = runner.summarize(rows, [], [TRAINING_SEED], worlds)
        self.assertEqual(complete["recurring"]["production_comparisons"]
                         ["rnn_minus_rnn_unread_at_test"]["mean_difference"], 2)
        for changed in (rows[:-1], rows[:-1] + [dict(rows[-1], status="failed", error="deliberate")]):
            result = runner.summarize(changed, [], [TRAINING_SEED], worlds)
            comparison = result["recurring"]["production_comparisons"]["rnn_minus_rnn_unread_at_test"]
            self.assertFalse(comparison["complete"])
            self.assertIsNone(comparison["mean_difference"])
            condition = result["recurring"]["conditions"]["rnn_unread_at_test"]
            self.assertEqual(condition["planned"], 2)
            self.assertEqual(condition["valid"], 1)
            self.assertEqual(condition["failed"] + condition["missing"], 1)

    def test_fork_denominators_keep_missing_failed_and_no_opportunity_separate(self):
        _, _, _, _, original, _ = self.fixture
        good = dict(copy.deepcopy(original), colony_production_difference=2,
                    recipient_differences=dict(original["recipient_differences"], produced=1),
                    other_citizens_production_difference=1)
        no_op = dict(training_seed=TRAINING_SEED, world_seed=WORLD_SEED + 1,
                     demand="recurring", slot="rnn_local", status="no_opportunity")
        failed = dict(no_op, world_seed=WORLD_SEED + 2, status="failed", error="deliberate")
        worlds = list(range(WORLD_SEED, WORLD_SEED + 4))
        result = runner.summarize([], [good, no_op, failed], [TRAINING_SEED], worlds)
        entry = result["recipient_stream_interventions"]["recurring:rnn_local"]
        self.assertEqual(tuple(entry[k] for k in ("planned", "retained", "valid", "no_opportunity", "failed", "missing")),
                         (4, 3, 1, 1, 1, 1))
        self.assertEqual(entry["conditional_mean_colony_production_difference"], 2)
        self.assertNotIn("exploratory_crossed_bootstrap_95_interval", entry)

    def test_duplicate_outcome_and_fork_slots_are_rejected(self):
        _, baseline, _, _, fork, _ = self.fixture
        with self.assertRaisesRegex(ValueError, "Duplicate evaluation"):
            runner.summarize([baseline, baseline], [], [TRAINING_SEED], [WORLD_SEED])
        with self.assertRaisesRegex(ValueError, "Duplicate recipient-fork"):
            runner.summarize([], [fork, fork], [TRAINING_SEED], [WORLD_SEED])

    def test_cli_retains_all_planned_slots_when_training_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            args = ["runner", "--episodes", "1", "--training-seeds", str(TRAINING_SEED),
                    "--worlds", "1", "--evaluation-seed-start", str(WORLD_SEED),
                    "--horizon", "1", "--workers", "1", "--output-dir", directory]
            with patch.object(sys, "argv", args), patch.object(runner, "train",
                    side_effect=RuntimeError("deliberate training failure")), redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as exit_:
                    runner.main()
            self.assertEqual(exit_.exception.code, 1)
            report = json.loads((Path(directory) / "report.json").read_text())
            self.assertEqual(len(report["runs"]), 2 * len(runner.SLOTS))
            self.assertEqual(len(report["recipient_forks"]), 2 * len(runner.FORK_SLOTS))
            self.assertTrue(all(t["status"] == "failed" for t in report["training"]))
            self.assertTrue(all(f["status"] == "failed" for f in report["recipient_forks"]))
            self.assertTrue(all(r["status"] == "failed" for r in report["runs"]
                                if r["condition"]["variant"] != "baseline"))
            self.assertTrue(all(r["status"] == "valid" for r in report["runs"]
                                if r["condition"]["variant"] == "baseline"))

    def test_cli_retains_counterfactual_failures_without_dropping_baselines(self):
        with tempfile.TemporaryDirectory() as directory:
            args = ["runner", "--episodes", "1", "--training-seeds", str(TRAINING_SEED),
                    "--worlds", "1", "--evaluation-seed-start", str(WORLD_SEED),
                    "--horizon", "1", "--workers", "1", "--output-dir", directory]
            with patch.object(sys, "argv", args), patch.object(runner, "train", side_effect=stub_training), patch.object(
                    runner, "recipient_fork", side_effect=RuntimeError("deliberate counterfactual failure")), redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as exit_:
                    runner.main()
            self.assertEqual(exit_.exception.code, 1)
            report = json.loads((Path(directory) / "report.json").read_text())
            self.assertEqual(len(report["runs"]), 2 * len(runner.SLOTS))
            self.assertTrue(all(r["status"] == "valid" for r in report["runs"]))
            self.assertEqual(len(report["recipient_forks"]), 2 * len(runner.FORK_SLOTS))
            self.assertTrue(all(f["status"] == "failed" for f in report["recipient_forks"]))
            self.assertTrue(all("deliberate counterfactual failure" in f["error"] for f in report["recipient_forks"]))
            persisted = [json.loads(line) for line in (Path(directory) / "recipient-forks.jsonl").read_text().splitlines()]
            self.assertEqual(persisted, report["recipient_forks"])


if __name__ == "__main__":
    unittest.main()
