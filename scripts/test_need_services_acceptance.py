"""Fail-closed evidence checks for the live service acceptance, not mock gameplay."""
import copy
import unittest

from rcon_need_services_acceptance import inventory_value, response_json, validate_chain


class EvidenceTest(unittest.TestCase):
    def events(self):
        job = "00000000-0000-4000-8000-000000000001"
        rows = [
            {"type": "NEED_OBSERVED", "citizen": "a", "request": "r", "observer": "a",
             "revision": 1, "observed_tick": 1},
            {"type": "OPTION_STARTED", "option": "CARRY_REQUEST", "citizen": "a", "request": "r"},
            {"type": "REQUEST_SENT", "citizen": "a", "request": "r", "packet": "p",
             "sender": "a", "recipient": "b", "revision": 1, "observer": "a", "observed_tick": 1},
            {"type": "REQUEST_RECEIVED", "citizen": "b", "request": "r", "packet": "p",
             "sender": "a", "recipient": "b", "revision": 1, "observer": "a", "observed_tick": 1},
            {"type": "SUPPLY_CLAIMED", "citizen": "b", "request": "r", "revision": 1,
             "origin": "REPORT", "selected_packet": "p", "commitment": "c"},
            {"type": "MOTOR_ASSIGNED", "citizen": "b", "request": "r", "job": job, "tick": 5,
             "revision": 1, "origin": "REPORT", "selected_packet": "p", "commitment": "c"},
            {"type": "TRANSFER_VERIFIED", "citizen": "b", "request": "r", "job": job,
             "tick": 20, "assigned_tick": 5, "delivered_tick": 20, "units": 1, "receipt": "native",
             "commitment": "c"},
        ]
        for sequence, row in enumerate(rows, 1):
            row["sequence"] = sequence
        return rows

    def test_inventory_is_independent_and_exact(self):
        self.assertEqual(inventory_value('Block has the following block data: []'), 0)
        self.assertEqual(inventory_value('Block data: [{Slot: 0b, id: "minecraft:wheat", Count: 6b}]'), 6)
        for invalid in ("transfers=6", '[{id:"minecraft:stone",Count:6b}]',
                        '[{id:"minecraft:wheat",Count:-1b}]', '[{id:"minecraft:wheat"}]'):
            with self.assertRaises(AssertionError):
                inventory_value(invalid)

    def test_trace_can_validate_without_claiming_inventory(self):
        checked = validate_chain(self.events(), 1)
        self.assertTrue(checked["request_recipient_job_chain"])
        self.assertNotIn("physical_inventory_witnessed", checked)

    def test_duplicate_job_receipt_is_rejected(self):
        rows = self.events()
        rows.append(copy.deepcopy(rows[-1]))
        with self.assertRaises(AssertionError):
            validate_chain(rows, 2)

    def test_unreceived_or_self_sent_request_cannot_pass(self):
        for changed in ("request", "citizen"):
            rows = self.events()
            rows[3][changed] = "other" if changed == "request" else "a"
            with self.assertRaises(AssertionError):
                validate_chain(rows, 1)

    def test_claim_or_intent_is_not_physical_completion(self):
        rows = self.events()
        rows[-1]["type"] = "SUPPLY_CLAIMED"
        with self.assertRaises(AssertionError):
            validate_chain(rows, 1)

    def test_packet_revision_and_selected_evidence_must_match(self):
        for key, value in (("selected_packet", "other"), ("revision", 2), ("origin", "DIRECT")):
            rows = self.events()
            rows[5][key] = value
            with self.assertRaises(AssertionError):
                validate_chain(rows, 1)

    def test_unrelated_observation_or_carry_does_not_prove_path(self):
        for index, key, value in ((0, "revision", 99), (1, "citizen", "other"),
                                  (2, "recipient", "other"), (4, "selected_packet", "other")):
            rows = self.events()
            rows[index][key] = value
            with self.assertRaises(AssertionError):
                validate_chain(rows, 1)

    def test_cross_actor_and_time_travel_receipts_fail(self):
        for key, value in (("citizen", "other"), ("delivered_tick", 4), ("receipt", None)):
            rows = self.events()
            rows[-1][key] = value
            with self.assertRaises(AssertionError):
                validate_chain(rows, 1)

    def test_status_marker_is_required(self):
        with self.assertRaises(AssertionError):
            response_json('{"enabled":true}', "NEED_SERVICES_STATUS")
        self.assertEqual(response_json('NEED_SERVICES_STATUS {"enabled":true}',
                                       "NEED_SERVICES_STATUS"), {"enabled": True})


if __name__ == "__main__":
    unittest.main()
