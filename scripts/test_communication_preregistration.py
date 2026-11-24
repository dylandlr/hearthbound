#!/usr/bin/env python3
"""Offline contracts for frozen arms, denominators, controls, and execution guard."""
import contextlib
import copy
from collections import Counter
import io
import itertools
import json
from pathlib import Path
import tempfile
import unittest

import communication_preregistration as protocol


class PreregistrationTests(unittest.TestCase):
    def setUp(self):
        self.value = protocol.document()

    def reject_rehashed_change(self, change):
        change(self.value["design"])
        self.value["design_sha256"] = protocol.digest(self.value["design"])
        with self.assertRaisesRegex(ValueError, "frozen v1 design"):
            protocol.validate_document(self.value)

    def test_committed_manifest_is_exact_reproducible_design(self):
        actual = protocol.load_document(protocol.DEFAULT_MANIFEST)
        self.assertEqual(actual, self.value)
        self.assertEqual(protocol.validate_document(actual), protocol.digest(actual["design"]))

    def test_144_worlds_and_24_complete_seed_blocks(self):
        body = self.value["design"]
        rows = body["planned_worlds"]
        self.assertEqual(len(rows), 144)
        self.assertEqual(len({row["trial_id"] for row in rows}), 144)
        self.assertEqual([row["execution_index"] for row in rows], list(range(1, 145)))
        self.assertEqual(Counter(row["arm"] for row in rows), {arm: 24 for arm in protocol.ARMS})
        self.assertFalse(set(protocol.WORLD_SEEDS) & set(protocol.PILOT_SEEDS))
        for block in body["blocks"]:
            matching = [row for row in rows if row["block_id"] == block["block_id"]]
            self.assertEqual([row["arm"] for row in matching], block["arm_order"])
            self.assertEqual({row["world_seed"] for row in matching}, {block["world_seed"]})
            self.assertEqual({row["policy_seed"] for row in matching}, {block["policy_seed"]})
            self.assertEqual(len({actor["citizen"] for actor in block["actors"]}), 4)

    def test_all_seat_permutations_and_hub_by_order_counterbalance(self):
        blocks = self.value["design"]["blocks"]
        self.assertEqual({tuple(block["slot_to_physical_seat"]) for block in blocks},
                         set(itertools.permutations(range(4))))
        for logical_slot in range(4):
            self.assertEqual(Counter(block["slot_to_physical_seat"][logical_slot] for block in blocks),
                             {seat: 6 for seat in range(4)})
        for hub_seat in range(4):
            subset = [block for block in blocks if block["slot_to_physical_seat"][0] == hub_seat]
            for arm in protocol.ARMS:
                self.assertEqual(Counter(block["arm_order"].index(arm) for block in subset),
                                 {position: 1 for position in range(6)})

    def test_exact_undirected_permission_graphs_not_new_all_to_all_arm(self):
        arms = {arm["arm"]: arm for arm in self.value["design"]["arms"]}
        complete = set(itertools.combinations(range(4), 2))
        edges = lambda name: {tuple(edge) for edge in arms[name]["undirected_permission_edges"]}
        self.assertEqual(edges("DIRECT"), complete)
        self.assertEqual(edges("DIRECT_UNREAD"), complete)
        self.assertEqual(edges("NO_MESSAGES"), set())
        self.assertEqual(edges("STAR"), {(0, 1), (0, 2), (0, 3)})
        self.assertEqual(edges("CHAIN"), {(0, 1), (1, 2), (2, 3)})
        self.assertEqual(edges("CYCLE"), {(0, 1), (0, 3), (1, 2), (2, 3)})
        self.assertNotIn("TREE", arms)
        self.assertNotIn("GRAPH", arms)
        transport = self.value["design"]["transport"]
        self.assertEqual(transport["range_blocks"], 12)
        self.assertFalse(transport["guaranteed_realized_connectivity"])
        self.assertFalse(transport["graph_structure_effect_isolated_from_cost"])

    def test_policy_seed_permutation_balances_every_physical_round_phase(self):
        blocks = self.value["design"]["blocks"]
        self.assertEqual(set(protocol.POLICY_SEEDS), set(range(65101, 65125)))
        unused = list(range(65101, 65125))
        for index, block in enumerate(blocks):
            first = (index // 6 + protocol.ORDER_OFFSETS[index % 6]) % 4
            expected_seed = next(seed for seed in unused if seed % 4 == first)
            self.assertEqual(block["policy_seed"], expected_seed)
            unused.remove(expected_seed)
        self.assertEqual(Counter(block["policy_seed"] % 4 for block in blocks),
                         {slot: 6 for slot in range(4)})
        for phase in range(4):
            self.assertEqual(Counter(block["slot_to_physical_seat"][(block["policy_seed"] + phase) % 4]
                                     for block in blocks), {seat: 6 for seat in range(4)})
        self.assertEqual(Counter(block["slot_to_physical_seat"][(block["policy_seed"] + round_) % 4]
                                 for block in blocks for round_ in range(30)),
                         {seat: 180 for seat in range(4)})
        for arm_order_offset in range(6):
            self.assertEqual(Counter(block["policy_seed"] % 4 for block in blocks[arm_order_offset::6]),
                             {slot: 1 for slot in range(4)})

    def test_unread_control_preserves_delivery_without_policy_exposure(self):
        arms = {arm["arm"]: arm for arm in self.value["design"]["arms"]}
        control = arms["DIRECT_UNREAD"]
        self.assertTrue(control["transport_enabled"])
        self.assertFalse(control["reports_exposed_to_decisions"])
        self.assertFalse(control["baseline_arm_supported"])
        self.assertTrue(arms["DIRECT"]["reports_exposed_to_decisions"])
        transport = self.value["design"]["transport"]
        self.assertFalse(transport["relaying"])
        self.assertFalse(transport["reports_change_direct_memory_by_delivery"])
        self.assertTrue(transport["selection_requires_own_fresh_positive_recheck"])

    def test_attempt_budget_cannot_buy_more_recipients_after_edge_denial(self):
        body = self.value["design"]
        self.assertEqual(body["budgets"]["max_send_attempts_per_world"],
                         4 * len(body["timing"]["relative_round_ticks"]))
        self.assertTrue(body["transport"]["denied_attempt_consumes_budget"])
        self.assertFalse(body["transport"]["retry_another_recipient_same_round"])
        self.assertFalse(body["budgets"]["unused_budget_transfer"])
        for sender in range(4):
            self.assertEqual(Counter((sender + 1 + round_ % 3) % 4 for round_ in range(30)),
                             {other: 10 for other in range(4) if other != sender})

    def test_guard_rejects_even_valid_manifest(self):
        with self.assertRaisesRegex(protocol.ExecutionBlocked, "OFFLINE DESIGN ONLY"):
            protocol.require_executable(self.value)

    def test_execution_flag_and_self_attested_binding_cannot_unlock(self):
        for change in (
            lambda body: body.update(execution_allowed=True),
            lambda body: body.update(runtime_binding={"commit": "a" * 40, "capabilities_passed": True}),
            lambda body: body["execution_gate"].update(this_module_can_execute=True),
        ):
            with self.subTest(change=change):
                self.value = protocol.document()
                self.reject_rehashed_change(change)

    def test_new_seed_replacement_or_missing_trial_remains_rejected_when_rehashed(self):
        for change in (
            lambda body: body["planned_worlds"][0].update(world_seed=99999),
            lambda body: body["planned_worlds"].pop(),
            lambda body: body["missingness_and_stopping"].update(missing_world_replacement=True),
        ):
            with self.subTest(change=change):
                self.value = protocol.document()
                self.reject_rehashed_change(change)

    def test_cost_horizon_control_and_primary_endpoint_cannot_drift(self):
        for change in (
            lambda body: body["timing"].update(horizon_game_ticks=1200),
            lambda body: body["budgets"].update(per_actor_round_send_attempts=2),
            lambda body: body["arms"][2].update(reports_exposed_to_decisions=True),
            lambda body: body["arms"][3]["undirected_permission_edges"].append([1, 2]),
            lambda body: body["outcomes"].update(primary="OUTPUT_TICKS"),
        ):
            with self.subTest(change=change):
                self.value = protocol.document()
                self.reject_rehashed_change(change)

    def test_missingness_retains_full_denominator_and_censored_times(self):
        body = self.value["design"]
        self.assertEqual(body["outcomes"]["primary_range"], [0, 4])
        self.assertFalse(body["missingness_and_stopping"]["setup_failure_is_zero_output"])
        self.assertFalse(body["outcomes"]["complete_output_required_for_validity"])
        self.assertEqual(body["outcomes"]["secondary"]["timing_difference"],
                         "NULL_IF_EITHER_MEMBER_CENSORED_OR_MISSING")
        self.assertIsNone(body["analysis"]["hypothesis_tests_or_winner_thresholds"])
        self.assertFalse(body["analysis"]["historical_cohorts_pooled"])
        self.assertFalse(body["analysis"]["citizens_messages_or_rounds_are_independent_replicates"])
        self.assertEqual(body["missingness_and_stopping"]["pre_world_dependency_setup_attempts"], 1)
        self.assertEqual(body["missingness_and_stopping"]["automatic_dependency_retries"], 0)

    def test_digest_and_strict_envelope_reject_corruption(self):
        for change in (
            lambda value: value.update(design_sha256="0" * 64),
            lambda value: value.update(schema="hearthbound.private-communication-plan.v1"),
            lambda value: value.update(execution_allowed=True),
            lambda value: value.pop("design_sha256"),
        ):
            with self.subTest(change=change):
                value = copy.deepcopy(self.value)
                change(value)
                with self.assertRaises(ValueError):
                    protocol.validate_document(value)

    def test_json_duplicate_keys_and_nonfinite_constants_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invalid.json"
            for raw in ('{"schema":"first","schema":"second"}', '{"design":NaN}',
                        '{"design":Infinity}'):
                path.write_text(raw, encoding="utf-8")
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    protocol.load_document(path)

    def test_writer_refuses_to_overwrite_existing_preregistration(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "design.json"
            protocol.write_document(path)
            first = path.read_bytes()
            self.assertEqual(protocol.load_document(path), self.value)
            with self.assertRaises(FileExistsError):
                protocol.write_document(path)
            self.assertEqual(path.read_bytes(), first)

    def test_cli_validates_but_executable_check_always_fails_without_mutation(self):
        before = protocol.DEFAULT_MANIFEST.read_bytes()
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(protocol.main(["validate"]), 0)
            self.assertEqual(protocol.main(["check-executable"]), 2)
        result = json.loads(output.getvalue())
        self.assertTrue(result["design_valid"])
        self.assertFalse(result["execution_allowed"])
        self.assertIn("OFFLINE DESIGN ONLY", errors.getvalue())
        self.assertEqual(protocol.DEFAULT_MANIFEST.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
