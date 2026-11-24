import unittest
from unittest.mock import patch

from distributed_demand_env import F
from probe_distributed_information import CASES, PROTOCOLS, build_fixture, run_case, run_probe, supplier_cargo


class InformationMechanismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_probe()

    def test_balanced_material_and_location_counterfactuals(self):
        report = self.report
        self.assertEqual((report["planned"], report["valid"], report["failed"]), (12, 12, 0))
        self.assertEqual(report["outputs_by_protocol"], dict(local=4, unread=2, no_messages=2))
        self.assertEqual(len({r["run_id"] for r in report["runs"]}), 12)
        for row in report["runs"]:
            self.assertEqual(row["metrics"]["produced"], int(row["selected_cargo_kind"] == row["required_kind"]))
            self.assertEqual(row["metrics"]["conservation_residual"], 0)
            self.assertEqual(row["metrics"]["demand_residual"], 0)
            self.assertEqual(row["metrics"]["work_started"], row["metrics"]["produced"])
        self.assertTrue(report["scripted_roles"])
        self.assertFalse(report["emergent_occupation_evidence"])

    def test_pre_choice_physics_actions_and_costs_are_matched(self):
        for node, kind in CASES:
            matched = [r for r in self.report["runs"] if (r["destination"], r["required_kind"]) == (node, kind)]
            first = matched[0]
            for other in matched[1:]:
                self.assertEqual(first["pre_choice"], other["pre_choice"])
                cutoff = first["decision_tick"]
                self.assertEqual(first["actions"][:cutoff], other["actions"][:cutoff])
                self.assertEqual(first["metrics"]["travel_ticks"], other["metrics"]["travel_ticks"])
                self.assertEqual(first["metrics"]["attempts"], other["metrics"]["attempts"])

    def test_transport_reading_and_real_work_remain_distinct(self):
        for row in self.report["runs"]:
            metrics, protocol = row["metrics"], row["communication"]
            self.assertEqual(metrics["attempts"], 1)
            self.assertEqual(metrics["delivered"], int(protocol != "no_messages"))
            self.assertEqual(metrics["read_report_inputs"] > 0, protocol == "local")
            self.assertEqual(row["supplier_observation"][F[f'workshop_{row["destination"]}_known']], int(protocol == "local"))
            verified = [e for e in row["events"] if e["event"] == "PRODUCT_VERIFIED"]
            self.assertEqual(sum(e["quantity"] for e in verified), metrics["produced"])
            self.assertTrue(all(e["consumed_kind"] == row["required_kind"] for e in verified))

    def test_setup_is_zero_tick_and_policy_uses_only_observation(self):
        world = build_fixture(2, 1, "local")
        self.assertEqual(world.tick, 0)
        self.assertEqual(world._schedule, {})
        self.assertEqual(world.metrics()["demand_issued"], 1)
        observation = world.obs(2)
        self.assertEqual(supplier_cargo(observation, 2), 0)
        world._orders[0].kind = 0
        self.assertEqual(world.obs(2), observation)
        self.assertEqual(supplier_cargo(world.obs(2), 2), 0)

    def test_failed_slot_stays_unknown_in_full_denominator(self):
        def fail_one(node, kind, protocol):
            if (node, kind, protocol) == (1, 0, "local"):
                raise RuntimeError("deliberate fixture failure")
            return run_case(node, kind, protocol)
        with patch("probe_distributed_information.run_case", side_effect=fail_one):
            report = run_probe()
        self.assertEqual((report["planned"], report["valid"], report["failed"]), (12, 11, 1))
        self.assertIsNone(report["outputs_by_protocol"]["local"])
        self.assertEqual(len(report["runs"]), 12)
        self.assertIn("deliberate fixture failure", report["runs"][0]["error"])


if __name__ == "__main__":
    unittest.main()
