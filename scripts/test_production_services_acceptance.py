"""Reject false production evidence; these tests are not simulated gameplay."""
import copy
import unittest

from rcon_production_services_acceptance import (
    ALLOWED_OUTPUTS, BUFFER, MILL, SOURCE, inventory_items, validate_production_chain,
)
from test_need_services_acceptance import EvidenceTest


class ProductionEvidenceTest(unittest.TestCase):
    def events(self):
        result = []
        for batch, units in enumerate((3, 1)):
            rows = EvidenceTest().events()
            job = f"00000000-0000-4000-8000-{batch + 1:012d}"
            commitment, packet = "c" + str(batch), "p" + str(batch)
            offset = batch * 100
            for row in rows:
                row["session"] = "session1"
                if "job" in row:
                    row["job"] = job
                if "commitment" in row:
                    row["commitment"] = commitment
                if "packet" in row:
                    row["packet"] = packet
                if "selected_packet" in row:
                    row["selected_packet"] = packet
                row["revision"] = batch + 1
                for key in ("tick", "observed_tick", "assigned_tick", "delivered_tick"):
                    if key in row:
                        row[key] += offset
            assigned, transferred = rows[-2:]
            assigned.update(source=list(SOURCE), destination=list(MILL), output_destination=list(BUFFER))
            assigned["assigned_tick"] = transferred["assigned_tick"]
            transferred.update(source=list(SOURCE), destination=list(MILL))
            common = {"citizen": "b", "request": "r", "job": job,
                      "commitment": commitment, "session": "session1"}
            items = {"create:wheat_flour": units}
            if batch == 0:
                items["minecraft:wheat_seeds"] = 1
            before_items = {} if batch == 0 else {"create:wheat_flour": 3, "minecraft:wheat_seeds": 1}
            after_items = {"create:wheat_flour": 3 if batch == 0 else 4, "minecraft:wheat_seeds": 1}
            rows.extend([
                {**common, "type": "PRODUCTION_OUTPUT_COLLECTED", "tick": offset + 40,
                 "processing_start_tick": offset + 21, "process_tick": offset + 39,
                 "wheat_before": 1, "wheat_after": 0, "flour_before": 0, "flour_after": units,
                 "units": units, "machine": list(MILL), "items": items,
                 "physical_evidence": "verified|" + job},
                {**common, "type": "PRODUCTION_OUTPUT_DELIVERED", "tick": offset + 50,
                 "units": units, "destination": list(BUFFER), "stock_before": 0 if batch == 0 else 3,
                 "stock_after": 3 if batch == 0 else 4, "items": items.copy(),
                 "items_before": before_items, "items_after": after_items},
                {**common, "type": "SERVICE_SETTLED", "tick": offset + 50,
                 "outcome": "VERIFIED_TRANSFER", "started_tick": offset + 5,
                 "duration_ticks": 45, "service_samples": batch + 1},
                {**common, "type": "PRODUCTION_SETTLED", "tick": offset + 50, "units": units,
                 "physical_evidence": "verified|" + job, "reservation_released": True,
                 "trace_retired": True, "production_samples": batch + 1, "service_samples": batch + 1,
                 "selected_packet": packet, "items": items.copy()},
                {"type": "POLICY_DECISION", "citizen": "b", "tick": offset + 51,
                 "selected": "wait", "scores": [{"id": "wait", "total": 0,
                                                    "production_samples": batch + 1}]},
            ])
            result.extend(rows)
        for sequence, row in enumerate(result, 1):
            row["sequence"] = sequence
        return result

    def changed(self, kind, key, value):
        rows = self.events()
        next(row for row in rows if row["type"] == kind)[key] = value
        return rows

    def test_variable_yield_and_byproducts_conserved(self):
        result = validate_production_chain(self.events())
        self.assertEqual(result["production_jobs"], 2)
        self.assertEqual(result["output_items"], {"create:wheat_flour": 4, "minecraft:wheat_seeds": 1})
        self.assertFalse(result["causal_communication_benefit_estimated"])

    def test_native_inventory_is_required(self):
        text = 'Block data: [{id:"create:wheat_flour",Count:3b},{id:"minecraft:wheat_seeds",Count:1b}]'
        self.assertEqual(inventory_items(text, ALLOWED_OUTPUTS),
                         {"create:wheat_flour": 3, "minecraft:wheat_seeds": 1})
        for bad in ("output_units=4", '[{id:"minecraft:wheat",Count:4b}]',
                    '[{id:"create:wheat_flour",Count:-1b}]'):
            with self.assertRaises(AssertionError):
                inventory_items(bad, ALLOWED_OUTPUTS)

    def test_input_or_callback_alone_is_not_delivery(self):
        for kind in ("PRODUCTION_OUTPUT_COLLECTED", "PRODUCTION_OUTPUT_DELIVERED", "PRODUCTION_SETTLED"):
            rows = self.changed(kind, "type", "UNVERIFIED_INTENTION")
            with self.assertRaises(AssertionError):
                validate_production_chain(rows)

    def test_wrong_owner_scope_endpoints_and_message_rejected(self):
        for kind, key, value in (
            ("PRODUCTION_SETTLED", "citizen", "a"),
            ("PRODUCTION_OUTPUT_COLLECTED", "session", "other"),
            ("TRANSFER_VERIFIED", "destination", list(BUFFER)),
            ("PRODUCTION_OUTPUT_DELIVERED", "destination", list(SOURCE)),
            ("PRODUCTION_SETTLED", "selected_packet", "other"),
        ):
            with self.subTest(kind=kind, key=key), self.assertRaises(AssertionError):
                validate_production_chain(self.changed(kind, key, value))

    def test_quantity_loss_time_travel_and_missing_release_rejected(self):
        for kind, key, value in (
            ("PRODUCTION_OUTPUT_COLLECTED", "flour_after", 2),
            ("PRODUCTION_OUTPUT_COLLECTED", "processing_start_tick", 19),
            ("PRODUCTION_OUTPUT_DELIVERED", "stock_after", 2),
            ("PRODUCTION_OUTPUT_DELIVERED", "items", {"create:wheat_flour": 3}),
            ("PRODUCTION_SETTLED", "reservation_released", False),
            ("PRODUCTION_SETTLED", "trace_retired", False),
        ):
            with self.subTest(kind=kind, key=key), self.assertRaises(AssertionError):
                validate_production_chain(self.changed(kind, key, value))

    def test_pooled_duplicate_learning_and_bypassed_policy_rejected(self):
        for kind, key, value in (
            ("PRODUCTION_SETTLED", "production_samples", 2),
            ("PRODUCTION_SETTLED", "service_samples", 0),
            ("POLICY_DECISION", "citizen", "a"),
            ("POLICY_DECISION", "selected", "unlogged"),
        ):
            with self.subTest(kind=kind, key=key), self.assertRaises(AssertionError):
                validate_production_chain(self.changed(kind, key, value))
        rows = self.events()
        decision = next(row for row in rows if row["type"] == "POLICY_DECISION")
        decision["scores"].append({"id": "better", "total": 1, "production_samples": 1})
        with self.assertRaises(AssertionError):
            validate_production_chain(rows)

    def test_missing_second_cycle_or_duplicate_physical_evidence_rejected(self):
        rows = self.events()
        with self.assertRaises(AssertionError):
            validate_production_chain(rows[:len(rows) // 2])
        settled = [row for row in rows if row["type"] == "PRODUCTION_SETTLED"]
        settled[1]["physical_evidence"] = settled[0]["physical_evidence"]
        with self.assertRaises(AssertionError):
            validate_production_chain(rows)

    def test_final_service_duration_and_item_witnesses_are_required(self):
        for kind, key, value in (
            ("SERVICE_SETTLED", "duration_ticks", 1),
            ("SERVICE_SETTLED", "tick", 40),
            ("SERVICE_SETTLED", "outcome", "VERIFIED_WAIT"),
            ("PRODUCTION_OUTPUT_COLLECTED", "physical_evidence", "unrelated"),
            ("PRODUCTION_OUTPUT_DELIVERED", "items_after", {"create:wheat_flour": 3}),
            ("PRODUCTION_OUTPUT_DELIVERED", "items_before", {"minecraft:wheat_seeds": 2}),
            ("PRODUCTION_SETTLED", "items", {"create:wheat_flour": 3}),
        ):
            with self.subTest(kind=kind, key=key), self.assertRaises(AssertionError):
                validate_production_chain(self.changed(kind, key, value))

    def test_private_decision_cannot_consult_future_production(self):
        rows = self.events()
        decision = next(row for row in rows if row["type"] == "POLICY_DECISION")
        decision["scores"][0]["production_samples"] = 2
        with self.assertRaises(AssertionError):
            validate_production_chain(rows)
        rows = self.changed("POLICY_DECISION", "tick", 49)
        with self.assertRaises(AssertionError):
            validate_production_chain(rows)


if __name__ == "__main__":
    unittest.main()
