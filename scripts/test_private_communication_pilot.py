#!/usr/bin/env python3
"""Adversarial protocol, provenance, transport and denominator contracts."""
import contextlib
import copy
import io
import struct
import unittest
from uuid import NAMESPACE_URL, uuid5

from private_communication_protocol import (
    DESTINATION, DIMENSION, HORIZON_TICKS, PLAN, POSITIONS, RUNTIME_SCHEMA,
    SEEDS, SOURCES, actor_uuid, digest, matched_manifest, planned_trial,
)
from rcon_private_communication_trial import (
    MultipartRcon, SETUP_COMMANDS, actor_witness, inventory, packed, read_frame,
    source_key, uuid_ints, validate_communication, validate_trial,
)
from rcon_two_citizen_haul_acceptance import packet
from summarize_private_communication_pilot import paired_summary


def identity(label):
    return str(uuid5(NAMESPACE_URL, "hearthbound-private-communication-test/" + label))


COUNTERS = ("idle_opportunities", "motor_ticks", "near_probes", "near_inspections",
            "outer_probes", "outer_inspections", "rechecks", "assignment_attempts",
            "assignments", "completed_jobs", "send_attempts", "report_reads",
            "motor_elapsed_ns", "discovery_elapsed_ns", "communication_elapsed_ns",
            "decision_elapsed_ns")
CAPS = ("near_probes", "near_inspections", "outer_probes", "outer_inspections",
        "rechecks", "assignment_attempts", "send_attempts")


def empty_communication(world, episode):
    audit = {key: 0 for key in ("send_attempts", "rejected_sends", "duplicate_sends",
             "messages", "events", "delivered", "read", "selected", "assigned",
             "physical_completed", "capacity_denials", "recording_errors", "send_records",
             "attempt_capacity_denials")}
    audit.update(world=world, episode=episode, history_quarantined="false",
                 strictly_read_only="true", causal_benefit_established="false")
    return {"audit": audit, "messages": [], "events": [], "attempts": []}


def zero_output_fixture(arm="NO_MESSAGES", seed=SEEDS[0]):
    """A full valid observation with 120 abstentions and zero physical output."""
    world, episode = identity("world"), identity("episode")
    configured = dict(schema=RUNTIME_SCHEMA, status="CONFIGURED", arm=arm, policy_seed=seed,
                      horizon_ticks=600, cadence_ticks=20, dimension=DIMENSION,
                      actor_count=0, rounds=0, records_total=0, destination=list(DESTINATION),
                      world=world, episode=episode, start_tick=None, end_tick=None,
                      observed_tick=50, elapsed_ticks=0, record_capacity_denials=0,
                      max_records=4096, errors=[], causal_benefit_established=False)
    started = dict(configured, status="SCHEDULED", actor_count=4, start_tick=100,
                   end_tick=700, observed_tick=80)
    records = []
    for relative in range(0, HORIZON_TICKS, 20):
        for slot in range(4):
            records.append(dict(sequence=len(records) + 1, kind="DECISION", tick=100 + relative,
                                relative_tick=relative, slot=slot, citizen=actor_uuid(seed, slot),
                                decision=identity(f"decision-{slot}-{relative}"), report_inputs=0,
                                result="ABSTAIN_NO_AVAILABLE_PRIVATE_SOURCE"))
    before, after, native = [], [], []
    for slot, position in enumerate(POSITIONS):
        actor = dict(slot=slot, citizen=actor_uuid(seed, slot), initial_position=list(position),
                     current_position=list(position), initial_no_ai=True, no_ai=True,
                     policy_id="SCRIPTED_PRIVATE_NEAREST_V1", private_sources=0, present=True,
                     active=False, phase=None, current_job=None, cargo_wheat=0,
                     counters={name: 0 for name in COUNTERS}, max_per_round={name: 0 for name in CAPS})
        before.append(copy.deepcopy(actor))
        actor["counters"].update(idle_opportunities=30, near_probes=2250, outer_probes=2250)
        actor["max_per_round"].update(near_probes=75, outer_probes=75)
        after.append(actor)
        native.append(dict(citizen=actor_uuid(seed, slot), no_ai=True, position=list(position),
                           rotation=[0.0, 0.0], cargo_wheat=0, motor=None))
    settings = {}
    for name, value in dict(matched_manifest(seed)["initial_game_rules"], daytime=6000).items():
        settings[name] = {"value": value, "raw": ("The time is 6000" if name == "daytime"
                         else f"Gamerule {name} is currently set to: {str(value).lower()}")}
    responses = []
    for command in SETUP_COMMANDS:
        if command.startswith("gamerule "):
            response = "Gamerule is now set to: false"
        elif command.startswith("time "):
            response = "Set the time to 6000"
        elif command.startswith("weather "):
            response = "Changing to clear weather"
        elif command.startswith("forceload "):
            response = "Marked chunks as force loaded"
        else:
            response = "Successfully filled 100 blocks"
        responses.append({"command": command, "response": response})
    inventories = {"sources": [{"wheat": 2}, {"wheat": 2}], "destination": {"wheat": 0}}
    comm = empty_communication(world, episode)
    final = dict(started, status="COMPLETE", rounds=30, records_total=len(records),
                 elapsed_ticks=600, observed_tick=700)
    return dict(declared_initial_manifest=matched_manifest(seed), setup_commands=responses,
                configured=configured, start=started, actors_before=before, actors_after=after,
                native_actors_before=copy.deepcopy(native), native_actors_after=copy.deepcopy(native),
                settings_before=settings, communication_before=copy.deepcopy(comm["audit"]),
                communication=comm, records=records, final=final, final_after_export=dict(final, observed_tick=720),
                inventories_before=copy.deepcopy(inventories), inventories_after=copy.deepcopy(inventories),
                inventories_after_export=copy.deepcopy(inventories), claims_after=0,
                active_interventions_after_start=0, horizon_wall_seconds=32.0)


def pending_direct_fixture():
    """A native accepted job still walking at the horizon is valid censored work."""
    data, seed = zero_output_fixture(), SEEDS[0]
    actor, native = data["actors_after"][0], data["native_actors_after"][0]
    citizen, job = actor["citizen"], identity("pending-job")
    decision = next(row for row in data["records"] if row["citizen"] == citizen)
    decision.update(result="SELECTED_FRESH_RECHECK", source=list(SOURCES[0]),
                    mode="DIRECT_MEMORY_RECHECK", evidence_observed_tick=100, report_id=None)
    common = dict(tick=100, relative_tick=0, slot=0, citizen=citizen)
    observation = dict(common, kind="OBSERVE", source=list(SOURCES[0]), observer=list(POSITIONS[0]),
                       state="AVAILABLE", wheat=2, reason="OBSERVED", revision=1)
    assigned = dict(common, kind="ASSIGNED", job=job, decision=decision["decision"],
                    source=list(SOURCES[0]), destination=list(DESTINATION), assigned_tick=100,
                    mode="DIRECT_MEMORY_RECHECK", report_id=None)
    data["records"] = [dict(observation, phase="NEAR"), dict(observation, phase="RECHECK"), decision,
                       assigned] + [row for row in data["records"] if row["citizen"] != citizen]
    data["records"].sort(key=lambda row: row["tick"])
    for sequence, row in enumerate(data["records"], 1):
        row["sequence"] = sequence
    actor.update(active=True, phase=0, current_job=job, private_sources=1)
    actor["counters"].update(idle_opportunities=1, motor_ticks=29, near_probes=75, outer_probes=75,
                             near_inspections=1, rechecks=1, assignment_attempts=1, assignments=1)
    actor["max_per_round"].update(near_inspections=1, rechecks=1, assignment_attempts=1)
    native["motor"] = dict(job=job, phase=0, source=packed(SOURCES[0]), destination=packed(DESTINATION), assignedTick=100)
    data["claims_after"] = 1
    data["final"]["records_total"] = data["final_after_export"]["records_total"] = len(data["records"])
    return data


def communication_chain(completed=True, failed_recheck=False):
    seed = SEEDS[0]
    world, episode = identity("world"), identity("episode")
    sender, recipient = actor_uuid(seed, 0), actor_uuid(seed, 1)
    message, attempt, decision, job = (identity(name) for name in ("message", "send", "cue", "job"))
    report_id = "actual-private-report"
    final = dict(world=world, episode=episode, start_tick=100, end_tick=700)
    observed = dict(kind="OBSERVE", sequence=1, citizen=sender, source=list(SOURCES[0]),
                    tick=100, revision=1, wheat=2, state="AVAILABLE")
    send = dict(kind="SEND", sequence=2, citizen=sender, recipient=recipient, source=list(SOURCES[0]), tick=100)
    choice = dict(citizen=recipient, tick=100, source=list(SOURCES[0]),
                  mode="REPORT_CUED_DIRECT_RECHECK", report_id=report_id,
                  evidence_observed_tick=100, report_inputs=1,
                  result="CUE_RECHECK_NOT_AVAILABLE" if failed_recheck else "SELECTED_FRESH_RECHECK")
    assigned = dict(citizen=recipient, decision=decision, source=list(SOURCES[0]),
                    mode="REPORT_CUED_DIRECT_RECHECK", report_id=report_id, assigned_tick=100)
    data = empty_communication(world, episode)
    data["messages"] = [dict(id=message, world=world, episode=episode, sender=sender, recipient=recipient,
                             report_id=report_id, source=source_key(SOURCES[0]), observed_tick=100,
                             sent_tick=100, delivered_tick=100, source_revision=1, reported_wheat=2,
                             expires_after_tick=300)]
    data["attempts"] = [dict(id=attempt, world=world, episode=episode, sender=sender, recipient=recipient,
                             source=source_key(SOURCES[0]), tick=100, outcome="DELIVERED", reason="ACCEPTED",
                             report_id=report_id)]
    events = [dict(stage="DELIVERED", tick=100, message_id=message, actor=recipient),
              dict(stage="READ", tick=100, message_id=message, actor=recipient, decision_id=decision),
              dict(stage="SELECTED", tick=100, message_id=message, actor=recipient, decision_id=decision)]
    assignments, completions = {}, {}
    if not failed_recheck:
        assignments[job] = assigned
        events.append(dict(stage="ASSIGNED", tick=100, message_id=message, actor=recipient,
                           decision_id=decision, job_id=job, destination=source_key(DESTINATION)))
        if completed:
            completions[job] = dict(delivered_tick=200)
            events.append(dict(stage="PHYSICAL_COMPLETED", tick=200, message_id=message, actor=recipient,
                               decision_id=decision, job_id=job, destination=source_key(DESTINATION),
                               wheat_transferred=1, witness="EXECUTOR_INSERTION_RETURNED_NO_REMAINDER"))
    for sequence, event in enumerate(events, 1):
        event["sequence"] = sequence
    data["events"] = events
    data["audit"].update(messages=1, delivered=1, send_attempts=1, send_records=1, events=len(events),
                         read=1, selected=1, assigned=len(assignments), physical_completed=len(completions))
    return data, final, seed, "DIRECT", {"OBSERVE": [observed], "SEND": [send]}, {decision: choice}, assignments, completions


class FragmentSocket:
    def __init__(self, data, split=7):
        self.data, self.split, self.received = data, split, 0
        self.sent, self.timeline = [], []

    def recv(self, size):
        chunk, self.data = self.data[:min(size, self.split)], self.data[min(size, self.split):]
        self.received += len(chunk)
        self.timeline.append(("recv", len(chunk)))
        return chunk

    def sendall(self, value):
        self.sent.append((value, self.received))
        self.timeline.append(("send", len(value)))


class TransportTests(unittest.TestCase):
    def test_large_multipart_response_and_two_sequential_commands(self):
        first, middle, last = "begin:", "x" * 5000, ":end"
        first_packet = packet(10, 0, first)
        sock = FragmentSocket(first_packet + packet(10, 0, middle) + packet(10, 0, last)
                              + packet(11, 0, "There are 0 players") + packet(12, 0, "next")
                              + packet(13, 0, "There are 0 players"), split=3)
        client = MultipartRcon(sock)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(client.run("large audit"), first + middle + last)
            self.assertEqual(client.run("next audit"), "next")
        self.assertEqual(sock.sent[0], (packet(10, 2, "large audit"), 0))
        self.assertEqual(sock.sent[1], (packet(11, 2, "list"), len(first_packet)))
        self.assertEqual(sock.sent[2][0], packet(12, 2, "next audit"))
        self.assertEqual(sock.sent[3][0], packet(13, 2, "list"))

    def test_bad_first_response_identity_or_kind(self):
        for request_id, kind in ((11, 0), (10, 2), (-1, 0)):
            with self.subTest(request_id=request_id, kind=kind), self.assertRaises(ValueError):
                MultipartRcon(FragmentSocket(packet(request_id, kind, "bad"))).run("audit")

    def test_foreign_fragment_and_empty_response_fail(self):
        for data in (packet(10, 0, "first") + packet(99, 0, "foreign"),
                     packet(10, 0, "") + packet(11, 0, "delimiter")):
            with self.subTest(data=data), self.assertRaises(ValueError):
                MultipartRcon(FragmentSocket(data)).run("audit")

    def test_malformed_length_terminator_encoding_and_disconnect(self):
        cases = (struct.pack("<i", 9), struct.pack("<i", 1_000_001),
                 packet(10, 0, "x")[:-1] + b"x", packet(10, 0, "x")[:-3] + b"\xff\0\0")
        for data in cases:
            with self.subTest(data=data), self.assertRaises((ValueError, UnicodeDecodeError)):
                read_frame(FragmentSocket(data, split=1))
        with self.assertRaises(ConnectionError):
            read_frame(FragmentSocket(packet(10, 0, "truncated")[:-1]))

    def test_total_response_budget_is_enforced(self):
        data = b"".join(packet(10, 0, "x" * 800_000) for _ in range(3))
        with self.assertRaisesRegex(ValueError, "Oversized multipart"):
            MultipartRcon(FragmentSocket(data, split=100_000)).run("audit")


class FixedReply:
    def __init__(self, response):
        self.response = response

    def require(self, command, expected):
        if expected not in self.response:
            raise ValueError("Missing expected response marker")
        return self.response


class NativeWitnessTests(unittest.TestCase):
    def test_actual_empty_and_wheat_snbt_inventory_shapes(self):
        for payload, count in (("[]", 0), ('[{Slot: 0b, id: "minecraft:wheat", Count: 2b}]', 2),
                               ('[{Count: 4b, Slot: 0b, id: "minecraft:wheat"}]', 4)):
            self.assertEqual(inventory(FixedReply("4, 101, 8 has the following block data: " + payload), SOURCES[0])["wheat"], count)

    def test_invalid_item_quantity_or_multiple_stacks_rejected(self):
        for payload in ('[{id: "minecraft:stone", Count: 2b}]', '[{id: "minecraft:wheat", Count: 0b}]',
                        '[{id: "minecraft:wheat", Count: 5b}]',
                        '[{id: "minecraft:wheat", Count: 1b},{id: "minecraft:wheat", Count: 1b}]'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                inventory(FixedReply("block data: " + payload), SOURCES[0])

    def test_native_entity_uuid_long_positions_and_cargo(self):
        citizen, job = actor_uuid(SEEDS[0], 0), identity("native-job")
        integers = ", ".join(map(str, uuid_ints(job)))
        haul = ('entity data: {phase: 1, source: ' + str(packed(SOURCES[0])) + 'L, destination: '
                + str(packed(DESTINATION)) + 'L, assignedTick: 100L, jobId: [I; ' + integers + ']}')

        class EntityReplies:
            def run(self, command):
                if command.startswith("execute if data"):
                    return "Test passed, count: 1"
                if command.endswith(" NoAI"):
                    return "entity data: 1b"
                if command.endswith(" Pos"):
                    return "entity data: [5.5d, 101.0d, -7.5d]"
                if command.endswith(" Rotation"):
                    return "entity data: [0.0f, -1.5f]"
                if command.endswith(".cargo"):
                    return 'entity data: {id: "minecraft:wheat", Count: 1b}'
                return haul

            def require(self, command, expected):
                response = self.run(command)
                if expected not in response:
                    raise ValueError("Missing expected native field")
                return response

        actual = actor_witness(EntityReplies(), citizen)
        self.assertEqual(actual["cargo_wheat"], 1)
        self.assertEqual(actual["position"], [5.5, 101.0, -7.5])
        self.assertEqual(actual["motor"]["job"], job)
        self.assertEqual(actual["motor"]["source"], packed(SOURCES[0]))
        self.assertEqual(actual["motor"]["assignedTick"], 100)


class PhysicalEvidenceTests(unittest.TestCase):
    def test_zero_output_is_valid_in_either_treatment(self):
        for arm in ("NO_MESSAGES", "DIRECT"):
            metrics = validate_trial(zero_output_fixture(arm), SEEDS[0], arm)
            self.assertEqual(metrics["physical_wheat_delivered"], 0)
            self.assertEqual(metrics["output_ticks"], 0)
            self.assertIsNone(metrics["first_delivery_relative_tick"])
            self.assertEqual(metrics["all_four_censored_at_tick"], 600)
            self.assertFalse(metrics["communication_win_required"])

    def test_pending_job_is_censored_not_discarded(self):
        metrics = validate_trial(pending_direct_fixture(), SEEDS[0], "NO_MESSAGES")
        self.assertEqual(metrics["unfinished_jobs"], 1)
        self.assertEqual(metrics["physical_wheat_delivered"], 0)
        self.assertEqual(metrics["inflight"][0]["phase"], 0)

    def test_direct_choice_cannot_be_justified_by_its_own_recheck(self):
        data = pending_direct_fixture()
        data["records"] = [row for row in data["records"] if not (row["kind"] == "OBSERVE" and row["phase"] == "NEAR")]
        for sequence, row in enumerate(data["records"], 1):
            row["sequence"] = sequence
        data["actors_after"][0]["counters"]["near_inspections"] = 0
        data["actors_after"][0]["max_per_round"]["near_inspections"] = 0
        data["final"]["records_total"] = data["final_after_export"]["records_total"] = len(data["records"])
        with self.assertRaisesRegex(ValueError, "own prior source observation"):
            validate_trial(data, SEEDS[0], "NO_MESSAGES")

    def test_unwitnessed_output_and_extra_sensor_calls_rejected(self):
        changed = zero_output_fixture()
        changed["inventories_after"]["destination"]["wheat"] = 1
        changed["inventories_after_export"] = copy.deepcopy(changed["inventories_after"])
        with self.assertRaisesRegex(ValueError, "completion receipts"):
            validate_trial(changed, SEEDS[0], "NO_MESSAGES")
        changed = zero_output_fixture()
        changed["actors_after"][0]["counters"]["near_inspections"] = 1
        with self.assertRaisesRegex(ValueError, "Unaccounted direct sensor"):
            validate_trial(changed, SEEDS[0], "NO_MESSAGES")

    def test_horizon_intervention_identity_and_freeze_mutations(self):
        mutations = (
            lambda data: data["final"].update(elapsed_ticks=599),
            lambda data: data.update(active_interventions_after_start=1),
            lambda data: data["actors_after"][0].update(citizen=identity("replacement")),
            lambda data: data["final_after_export"].update(records_total=121),
        )
        for mutate in mutations:
            data = zero_output_fixture(); mutate(data)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                validate_trial(data, SEEDS[0], "NO_MESSAGES")


class CommunicationEvidenceTests(unittest.TestCase):
    def test_complete_actual_message_chain(self):
        metrics = validate_communication(*communication_chain())
        self.assertEqual(metrics["report_cued_physical_jobs"], 1)
        self.assertEqual(metrics["never_selected_messages"], 0)
        self.assertEqual(metrics["expired_by_horizon"], 1)

    def test_delivery_without_completion_does_not_count_physical_output(self):
        metrics = validate_communication(*communication_chain(completed=False))
        self.assertEqual(metrics["delivered_messages"], 1)
        self.assertEqual(metrics["report_cued_assignments"], 1)
        self.assertEqual(metrics["report_cued_physical_jobs"], 0)

    def test_failed_recheck_still_requires_actual_selection_and_original_observation_tick(self):
        args = communication_chain(failed_recheck=True)
        self.assertEqual(validate_communication(*args)["report_cued_physical_jobs"], 0)
        no_selection = copy.deepcopy(args)
        no_selection[0]["events"] = no_selection[0]["events"][:-1]
        no_selection[0]["audit"].update(events=2, selected=0)
        with self.assertRaisesRegex(ValueError, "lost selection evidence"):
            validate_communication(*no_selection)
        wrong_observation = copy.deepcopy(args)
        next(iter(wrong_observation[5].values()))["evidence_observed_tick"] = 99
        with self.assertRaisesRegex(ValueError, "unread or different report"):
            validate_communication(*wrong_observation)

    def test_cross_actor_job_or_observation_provenance_rejected(self):
        mutations = (
            lambda args: args[0]["messages"][0].update(recipient=actor_uuid(SEEDS[0], 2)),
            lambda args: args[0]["messages"][0].update(observed_tick=99),
            lambda args: args[0]["events"][-1].update(job_id=identity("foreign-job")),
            lambda args: args[4]["OBSERVE"][0].update(sequence=3),
            lambda args: args[0]["events"][1].update(tick=301),
        )
        for mutate in mutations:
            args = communication_chain(); mutate(args)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                validate_communication(*args)

    def test_isolated_arm_cannot_inherit_a_delivered_report(self):
        args = list(communication_chain()); args[3] = "NO_MESSAGES"
        with self.assertRaisesRegex(ValueError, "Isolated arm transmitted"):
            validate_communication(*args)


def summary_rows():
    rows = []
    for plan in PLAN:
        metrics = dict(physical_wheat_delivered=0, output_ticks=0,
                       first_delivery_relative_tick=None, all_four_delivery_relative_tick=None,
                       costs={"near_inspections": 0, "report_reads": 0}, direct_only_physical_jobs=0,
                       communication={"report_cued_physical_jobs": 0})
        rows.append(dict(plan, status="VALID_OBSERVATION", metrics=metrics,
                         world_uuid=identity("world-" + plan["trial_id"]),
                         episode=identity("episode-" + plan["trial_id"]),
                         matched_initial_manifest_sha256=digest(matched_manifest(plan["seed"]))))
    return rows


class PairedDenominatorTests(unittest.TestCase):
    def test_plan_has_fixed_six_worlds_and_stable_actor_slots(self):
        self.assertEqual(len(PLAN), 6)
        self.assertEqual(len({row["trial_id"] for row in PLAN}), 6)
        for seed in SEEDS:
            pair = [row for row in PLAN if row["seed"] == seed]
            self.assertEqual({row["arm"] for row in pair}, {"NO_MESSAGES", "DIRECT"})
            self.assertEqual(pair[0]["policy_seed"], pair[1]["policy_seed"])
            self.assertEqual(len({actor_uuid(seed, slot) for slot in range(4)}), 4)
        with self.assertRaises(ValueError):
            planned_trial("unplanned-retry")

    def test_equal_and_worse_communication_results_are_retained(self):
        rows = summary_rows()
        for index, (left, right) in enumerate(((1, 2), (2, 2), (3, 1))):
            rows[index * 2]["metrics"]["physical_wheat_delivered"] = left
            rows[index * 2 + 1]["metrics"]["physical_wheat_delivered"] = right
        result = paired_summary(rows)
        self.assertEqual(result["primary_paired_deltas"], [1, 0, -2])
        self.assertEqual(result["valid_world_observations"], 6)
        self.assertEqual(result["direct_lower_pairs"], 1)
        self.assertEqual(result["equal_output_pairs"], 1)
        self.assertFalse(result["performance_win_required"])
        self.assertFalse(result["causal_benefit_established"])

    def test_missing_world_retains_planned_pair_and_censors_latency_delta(self):
        rows = summary_rows()
        rows[1].update(status="MISSING", metrics=None)
        rows[2]["metrics"]["first_delivery_relative_tick"] = 120
        result = paired_summary(rows)
        self.assertEqual(result["planned_worlds"], 6)
        self.assertEqual(result["invalid_or_missing_worlds"], 1)
        self.assertEqual(result["invalid_or_incomplete_pairs"], 1)
        self.assertIsNone(result["pairs"][0]["delta_direct_minus_isolated"])
        self.assertIsNone(result["pairs"][1]["delta_direct_minus_isolated"]["first_delivery_relative_tick"])

    def test_absent_mechanism_coverage_is_not_an_invalid_world(self):
        result = paired_summary(summary_rows())
        self.assertEqual(result["valid_paired_observations"], 3)
        self.assertFalse(result["mechanism_coverage"]["complete_report_cued_delivery_chain_exercised"])
        self.assertEqual(result["primary_paired_deltas"], [0, 0, 0])

    def test_missing_denominator_reused_world_and_mismatched_manifest_rejected(self):
        with self.assertRaisesRegex(ValueError, "denominator changed"):
            paired_summary(summary_rows()[:-1])
        rows = summary_rows(); rows[1]["world_uuid"] = rows[0]["world_uuid"]
        with self.assertRaisesRegex(ValueError, "not independent"):
            paired_summary(rows)
        rows = summary_rows(); rows[1]["matched_initial_manifest_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "manifests differ"):
            paired_summary(rows)


if __name__ == "__main__":
    unittest.main()
