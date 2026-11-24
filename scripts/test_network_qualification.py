#!/usr/bin/env python3
"""Adversarial contracts for engineering network qualification and native evidence."""
import copy
import gzip
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from network_qualification_protocol import (
    ARMS, BLOCK_ID, CAPABILITY_REQUIREMENTS, DESIGN_SHA256, DESTINATION, DIMENSION, EDGES,
    HORIZON_TICKS, PLAN, POLICY_SEED, POSITIONS, RUNTIME_SCHEMA, SLOT_TO_SEAT, SOURCES,
    SCHEMA, WORLD_SEED, actor_uuid, digest, initial_manifest as matched_manifest, parse_json, plan_document,
)
from network_qualification_native import (
    CommunicationNbtReader, SnbtReader, expected_report, inbox_witness, native_uuid,
    normalize_inbox, replay_inboxes, validate_inbox_witness,
)
from rcon_network_qualification import (
    SETUP_COMMANDS, packed, source_key, trial_id, uuid_ints, validate_trial,
)
from summarize_network_qualification import capability_coverage, qualification_summary, summarize
from uuid import NAMESPACE_URL, uuid5
import run_network_qualification as runner

COUNTERS = ("idle_opportunities", "motor_ticks", "near_probes", "near_inspections",
            "outer_probes", "outer_inspections", "rechecks", "assignment_attempts",
            "assignments", "completed_jobs", "send_attempts", "report_reads",
            "motor_elapsed_ns", "discovery_elapsed_ns", "communication_elapsed_ns", "decision_elapsed_ns")
CAPS = ("near_probes", "near_inspections", "outer_probes", "outer_inspections",
        "rechecks", "assignment_attempts", "send_attempts")


def identity(label):
    return str(uuid5(NAMESPACE_URL, "hearthbound-network-qualification-test/" + label))


def empty_communication(world, episode):
    audit = {key: 0 for key in ("send_attempts", "rejected_sends", "duplicate_sends",
             "messages", "events", "delivered", "read", "selected", "assigned",
             "physical_completed", "capacity_denials", "recording_errors", "send_records",
             "attempt_capacity_denials")}
    audit.update(world=world, episode=episode, history_quarantined="false",
                 strictly_read_only="true", causal_benefit_established="false")
    return {"audit": audit, "messages": [], "events": [], "attempts": []}


def zero_output_fixture(arm="NO_MESSAGES", seed=WORLD_SEED):
    """A full valid observation with 120 abstentions and zero physical output."""
    world, episode = identity("world"), identity("episode")
    configured = dict(schema=RUNTIME_SCHEMA, status="CONFIGURED", arm=arm, policy_seed=POLICY_SEED,
                      horizon_ticks=600, cadence_ticks=20, dimension=DIMENSION,
                      actor_count=0, rounds=0, records_total=0, destination=list(DESTINATION),
                      world=world, episode=episode, start_tick=None, end_tick=None,
                      observed_tick=50, elapsed_ticks=0, record_capacity_denials=0,
                      max_records=4096, errors=[], causal_benefit_established=False)
    started = dict(configured, status="SCHEDULED", actor_count=4, start_tick=100,
                   end_tick=700, observed_tick=80)
    common = dict(world=world, episode=episode, arm=arm, block_id=BLOCK_ID,
                  trial_id=trial_id(arm), design_sha256=DESIGN_SHA256, qualification_only=True)
    configured.update(common, kind="audit", read_only=True, slot_to_seat=list(SLOT_TO_SEAT),
                      undirected_permission_edges=EDGES[arm], transport_enabled=arm != "NO_MESSAGES",
                      reports_exposed_to_decisions=arm not in ("NO_MESSAGES", "DIRECT_UNREAD"))
    started = dict(configured, status="SCHEDULED", actor_count=4, start_tick=100, end_tick=700, observed_tick=80)
    records = []
    for round_number in range(30):
        first = (POLICY_SEED % 4 + round_number % 4) % 4
        order = [(first + index) % 4 for index in range(4)]
        for slot in order:
            peer = (slot + 1 + round_number % 3) % 4
            edge = sorted((slot, peer))
            row = dict(common, sequence=len(records) + 1, kind="SEND_OPPORTUNITY", tick=100 + round_number * 20,
                       relative_tick=round_number * 20, round=round_number, slot=slot,
                       physical_seat=SLOT_TO_SEAT[slot], citizen=actor_uuid(seed, slot),
                       recipient=actor_uuid(seed, peer), recipient_slot=peer, recipient_seat=SLOT_TO_SEAT[peer],
                       permission_edge=edge, edge_allowed=edge in EDGES[arm], route=[actor_uuid(seed, slot), actor_uuid(seed, peer)],
                       route_semantics="PROPOSED_DIRECT_RECIPIENT", edge_decision="NOT_ATTEMPTED_NO_PAYLOAD",
                       charged_send_budget=0, result="NO_ELIGIBLE_DIRECT_EVIDENCE")
            row.update({key: None for key in ("attempt_id", "source", "source_observation_owner", "observed_tick",
                       "source_revision", "claimed_wheat", "source_state", "observation_world", "observation_episode")})
            records.append(row)
        for slot in order:
            records.append(dict(common, sequence=len(records) + 1, kind="DECISION", tick=100 + round_number * 20,
                                relative_tick=round_number * 20, round=round_number, physical_seat=SLOT_TO_SEAT[slot],
                                slot=slot, citizen=actor_uuid(seed, slot), decision=identity(f"decision-{slot}-{round_number}"),
                                report_inputs=0, private_source_candidates=0, claimed_candidates=0,
                                result="ABSTAIN_NO_AVAILABLE_PRIVATE_SOURCE"))
    before, after, native = [], [], []
    for slot, position in enumerate(POSITIONS):
        actor = dict(slot=slot, physical_seat=SLOT_TO_SEAT[slot], motor_status="IDLE", citizen=actor_uuid(seed, slot), initial_position=list(position),
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
            response = "Set the weather to clear\n"
        elif command.startswith("forceload "):
            response = "Marked chunks as force loaded"
        else:
            response = "Successfully filled 100 blocks"
        responses.append({"command": command, "response": response})
    inventories = {"sources": [{"wheat": 2}, {"wheat": 2}], "destination": {"wheat": 0}}
    comm = empty_communication(world, episode)
    final = dict(started, status="COMPLETE", rounds=30, records_total=len(records),
                 elapsed_ticks=600, observed_tick=700)
    inboxes = [dict(citizen=actor_uuid(seed, slot), status="ABSENT_AT_NATIVE_PROBE",
                    presence_raw="Test failed\n", raw=None, entries=[]) for slot in range(4)]
    return dict(polls=[copy.deepcopy(final)], native_actors_after_export=copy.deepcopy(native),
                native_inboxes_before=copy.deepcopy(inboxes), native_inboxes_after=copy.deepcopy(inboxes),
                native_inboxes_after_export=copy.deepcopy(inboxes), declared_initial_manifest=matched_manifest(seed), setup_commands=responses,
                configured=configured, start=started, actors_before=before, actors_after=after,
                native_actors_before=copy.deepcopy(native), native_actors_after=copy.deepcopy(native),
                settings_before=settings, communication_before=copy.deepcopy(comm["audit"]),
                communication=comm, records=records, final=final, final_after_export=dict(final, observed_tick=720),
                inventories_before=copy.deepcopy(inventories), inventories_after=copy.deepcopy(inventories),
                inventories_after_export=copy.deepcopy(inventories), claims_after=0,
                active_interventions_after_start=0, horizon_wall_seconds=32.0)


def snbt(value):
    if isinstance(value, dict):
        return '{' + ','.join(key + ':' + snbt(item) for key, item in value.items()) + '}'
    if isinstance(value, tuple):
        return '[I;' + ','.join(str(item) for item in value) + ']'
    if isinstance(value, list):
        return '[' + ','.join(snbt(item) for item in value) + ']'
    return json.dumps(value)


def inbox_record(citizen, entries):
    native = copy.deepcopy(entries)
    for report in native:
        for key in ("observationWorld", "observationSession", "sender", "recipient"):
            report[key] = tuple(uuid_ints(report[key]))
    payload = {"schema": "hearthbound.citizen-reports.v1", "entries": native}
    return dict(citizen=citizen, status="OBSERVED_NATIVE_INBOX", presence_raw="Test passed, count: 1\n",
                raw="TrialWorker has the following entity data: " + snbt(payload) + "\n", entries=entries)


def one_send_fixture(arm="DIRECT_UNREAD"):
    """One genuine direct payload; its sender accepts a pending job at the last round."""
    data = zero_output_fixture(arm)
    rows = data["records"]
    send = next(row for row in rows if row["kind"] == "SEND_OPPORTUNITY" and row["round"] == 29 and row["slot"] == 0)
    decision = next(row for row in rows if row["kind"] == "DECISION" and row["round"] == 29 and row["slot"] == 0)
    actor, native = data["actors_after"][0], data["native_actors_after"][0]
    base = {key: send[key] for key in ("world", "episode", "arm", "block_id", "trial_id", "design_sha256",
                                     "qualification_only", "tick", "relative_tick", "round", "physical_seat", "slot", "citizen")}
    observed = dict(base, kind="OBSERVE", phase="OUTER", source=list(SOURCES[0]), observer=list(POSITIONS[0]),
                    state="AVAILABLE", wheat=2, reason="OBSERVED", revision=1)
    job = identity("pending-job")
    decision.update(result="SELECTED_FRESH_RECHECK", private_source_candidates=1, source=list(SOURCES[0]),
                    mode="DIRECT_MEMORY_RECHECK", report_id=None, evidence_observed_tick=680)
    assignment = dict(base, kind="ASSIGNED", job=job, decision=decision["decision"], source=list(SOURCES[0]),
                      destination=list(DESTINATION), assigned_tick=680, mode="DIRECT_MEMORY_RECHECK", report_id=None)
    rows.insert(next(index for index, row in enumerate(rows) if row["round"] == 29), observed)
    index = rows.index(decision)
    rows.insert(index, dict(observed, phase="RECHECK"))
    rows.insert(rows.index(decision) + 1, assignment)
    allowed = [0, 3] in EDGES[arm]
    permission = "NETWORK_DISABLED" if arm == "NO_MESSAGES" else "ALLOWED" if allowed else "TOPOLOGY_BLOCKED"
    send.update(kind="SEND", charged_send_budget=1, attempt_id=identity("attempt"), source=list(SOURCES[0]),
                source_observation_owner=actor["citizen"], observed_tick=680, source_revision=1, claimed_wheat=2,
                source_state="AVAILABLE", observation_world=send["world"], observation_episode=send["episode"],
                edge_decision=permission, route_semantics="ATTEMPTED_DIRECT_RECIPIENT",
                result="KNOWLEDGE_SHARE status=DELIVERED action_authorized=false" if allowed else "REJECTED_" + permission)
    attempt = dict(id=send["attempt_id"], world=send["world"], episode=send["episode"], sender=send["citizen"],
                   recipient=send["recipient"], source=source_key(SOURCES[0]), tick=680,
                   outcome="DELIVERED" if allowed else "REJECTED",
                   reason="ACCEPTED_RECIPIENT_INBOX" if allowed else permission)
    comm = data["communication"]
    comm["attempts"] = [attempt]
    comm["audit"].update(send_attempts=1, send_records=1, rejected_sends=0 if allowed else 1)
    if allowed:
        report_id = "actual-owned-observation"
        attempt["report_id"] = report_id
        message = dict(id=identity("message"), world=send["world"], episode=send["episode"], sender=send["citizen"],
                       recipient=send["recipient"], report_id=report_id, source=source_key(SOURCES[0]),
                       observed_tick=680, sent_tick=680, delivered_tick=680, source_revision=1,
                       reported_wheat=2, expires_after_tick=880, transport="EXPLICIT_LOCAL_SYNCHRONOUS")
        comm["messages"] = [message]
        comm["events"] = [dict(sequence=1, stage="DELIVERED", tick=680, message_id=message["id"], actor=send["recipient"])]
        comm["audit"].update(messages=1, delivered=1, events=1)
        data["native_inboxes_after"][3] = inbox_record(send["recipient"], [expected_report(message)])
        data["native_inboxes_after_export"] = copy.deepcopy(data["native_inboxes_after"])
    actor.update(private_sources=1, active=True, phase=0, current_job=job)
    actor["counters"].update(outer_inspections=1, rechecks=1, send_attempts=1, assignment_attempts=1, assignments=1)
    actor["max_per_round"].update(outer_inspections=1, rechecks=1, send_attempts=1, assignment_attempts=1)
    native["motor"] = dict(job=job, phase=0, source=packed(SOURCES[0]), destination=packed(DESTINATION), assignedTick=680)
    data["native_actors_after_export"] = copy.deepcopy(data["native_actors_after"])
    data["claims_after"] = 1
    for index, row in enumerate(rows, 1):
        row["sequence"] = index
    for audit in (data["final"], data["final_after_export"], *data["polls"]):
        audit["records_total"] = len(rows)
    return data


def read_without_selection_fixture():
    """An actual inbox read attached to an abstaining decision, with no job credit."""
    data = one_send_fixture("DIRECT")
    decision = next(row for row in data["records"] if row["kind"] == "DECISION"
                    and row["round"] == 29 and row["slot"] == 3)
    decision["report_inputs"] = 1
    data["actors_after"][3]["counters"]["report_reads"] = 1
    data["communication"]["events"].append(dict(sequence=2, stage="READ", tick=680,
        actor=decision["citizen"], message_id=identity("message"), decision_id=decision["decision"]))
    data["communication"]["audit"].update(read=1, events=2)
    return data


class NetworkEvidenceTests(unittest.TestCase):
    def test_all_six_zero_output_conditions_are_valid_but_unexercised(self):
        for arm in ARMS:
            with self.subTest(arm=arm):
                metrics = validate_trial(zero_output_fixture(arm), WORLD_SEED, arm)
                self.assertEqual(metrics["physical_wheat_delivered"], 0)
                self.assertIsNone(metrics["first_delivery_relative_tick"])
                self.assertIsNone(metrics["all_four_delivery_relative_tick"])
                self.assertEqual(metrics["all_four_censored_at_tick"], 600)
                self.assertEqual(metrics["network"]["communication_opportunities"], 120)
                self.assertEqual(capability_coverage(arm, metrics)["status"], "NOT_EXERCISED")

    def test_truthful_unread_delivery_and_pending_native_job_are_valid(self):
        metrics = validate_trial(one_send_fixture(), WORLD_SEED, "DIRECT_UNREAD")
        self.assertEqual(metrics["communication"]["delivered_messages"], 1)
        self.assertEqual(metrics["communication"]["policy_reads"], 0)
        self.assertEqual(metrics["unfinished_jobs"], 1)
        self.assertEqual(metrics["physical_wheat_delivered"], 0)
        self.assertEqual(capability_coverage("DIRECT_UNREAD", metrics)["status"], "EXERCISED")

    def test_network_disabled_and_forbidden_edges_consume_attempt(self):
        for arm, field in (("NO_MESSAGES", "network_disabled_attempts"), ("CHAIN", "topology_blocked_attempts")):
            with self.subTest(arm=arm):
                metrics = validate_trial(one_send_fixture(arm), WORLD_SEED, arm)
                self.assertEqual(metrics["network"][field], 1)
                self.assertEqual(metrics["communication"]["delivered_messages"], 0)
                self.assertEqual(metrics["costs"]["send_attempts"], 1)
                sender = metrics["actor_metrics"][0]
                self.assertEqual(sender["send_outcomes"], {"DELIVERED": 0, "DUPLICATE": 0, "REJECTED": 1})
                self.assertEqual(sender["rejection_reasons"],
                                 {"NETWORK_DISABLED" if arm == "NO_MESSAGES" else "TOPOLOGY_BLOCKED": 1})
                self.assertEqual(sender["job_chains"][0]["status"], "PENDING_AT_HORIZON")
                self.assertIsNone(sender["job_chains"][0]["delivered_tick"])

    def test_per_citizen_read_attribution_cannot_be_swapped(self):
        data = read_without_selection_fixture()
        metrics = validate_trial(data, WORLD_SEED, "DIRECT")
        self.assertEqual(metrics["communication"]["policy_reads"], 1)
        sender, recipient = metrics["actor_metrics"][0], metrics["actor_metrics"][3]
        self.assertEqual((sender["delivered_sent"], sender["policy_reads"]), (1, 0))
        self.assertEqual((recipient["delivered_received"], recipient["policy_reads"], recipient["selected_reports"]), (1, 1, 0))
        self.assertEqual(recipient["inbox_lifecycle"]["retained"], 1)
        self.assertEqual(recipient["physical_wheat_delivered"], 0)
        data["actors_after"][0]["counters"]["report_reads"] = 1
        data["actors_after"][3]["counters"]["report_reads"] = 0
        with self.assertRaisesRegex(ValueError, "own actual READ"):
            validate_trial(data, WORLD_SEED, "DIRECT")

    def test_capability_needs_both_topology_paths(self):
        metrics = validate_trial(one_send_fixture("CHAIN"), WORLD_SEED, "CHAIN")
        self.assertEqual(capability_coverage("CHAIN", metrics)["unmet_requirements"], ["allowed_transport_attempts_min"])
        metrics["network"]["allowed_transport_attempts"] = 1
        self.assertEqual(capability_coverage("CHAIN", metrics)["status"], "EXERCISED")

    def invalid(self, mutate, factory=one_send_fixture, arm="DIRECT_UNREAD"):
        data = factory()
        mutate(data)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            validate_trial(data, WORLD_SEED, arm)

    def test_removed_opportunity_rejected(self):
        self.invalid(lambda data: data["records"].pop(0))

    def test_extra_same_round_attempt_rejected(self):
        self.invalid(lambda data: data["records"].insert(0, copy.deepcopy(data["records"][0])))

    def test_permitted_graph_cannot_be_changed(self):
        self.invalid(lambda data: data["final"].update(undirected_permission_edges=[]))

    def test_seat_and_uuid_are_bound(self):
        for mutate in (lambda data: data["actors_after"][0].update(physical_seat=0),
                       lambda data: data["records"][0].update(citizen=actor_uuid(WORLD_SEED, 1))):
            self.invalid(mutate)

    def test_foreign_run_design_and_extra_audit_field_rejected(self):
        for values in ({"design_sha256": "0" * 64}, {"trial_id": "qual-direct"}, {"unapproved": True}):
            self.invalid(lambda data, values=values: data["final"].update(values))

    def test_unread_policy_inputs_and_selections_rejected(self):
        self.invalid(lambda data: next(row for row in data["records"] if row["kind"] == "DECISION").update(report_inputs=1))
        self.invalid(lambda data: data["communication"]["events"].append(dict(sequence=2, stage="READ", tick=680,
             actor=actor_uuid(WORLD_SEED, 3), message_id=identity("message"), decision_id=identity("bogus-decision"))))

    def test_send_must_use_exact_native_attempt_and_own_source(self):
        for values in ({"attempt_id": identity("wrong-attempt")}, {"source_observation_owner": actor_uuid(WORLD_SEED, 3)},
                       {"observed_tick": 660}, {"source_revision": 2}, {"claimed_wheat": 1}):
            self.invalid(lambda data, values=values: next(row for row in data["records"] if row["kind"] == "SEND").update(values))

    def test_no_relay_and_no_alternate_peer_retry(self):
        for values in ({"route": [actor_uuid(WORLD_SEED, 0), actor_uuid(WORLD_SEED, 1), actor_uuid(WORLD_SEED, 3)]},
                       {"recipient_slot": 1}, {"permission_edge": [0, 1]}, {"charged_send_budget": 0}):
            self.invalid(lambda data, values=values: next(row for row in data["records"] if row["kind"] == "SEND").update(values))

    def test_no_payload_cannot_charge_or_invent_attempt(self):
        for values in ({"charged_send_budget": 1}, {"attempt_id": identity("invented")}, {"source": list(SOURCES[0])}):
            self.invalid(lambda data, values=values: data["records"][0].update(values))

    def test_discovery_after_send_is_rejected(self):
        def mutate(data):
            rows = data["records"]
            observation = next(row for row in rows if row["kind"] == "OBSERVE" and row["phase"] == "OUTER")
            rows.remove(observation); rows.insert(next(i for i, row in enumerate(rows) if row["kind"] == "SEND") + 1, observation)
            for i, row in enumerate(rows, 1): row["sequence"] = i
        self.invalid(mutate)

    def test_same_tick_decision_priority_swap_is_rejected(self):
        def mutate(data):
            rows = data["records"]
            indexes = [i for i, row in enumerate(rows) if row["kind"] == "DECISION" and row["round"] == 0]
            rows[indexes[0]], rows[indexes[1]] = rows[indexes[1]], rows[indexes[0]]
            for i, row in enumerate(rows, 1): row["sequence"] = i
        self.invalid(mutate)

    def test_native_inbox_cannot_be_deleted_or_rewritten(self):
        self.invalid(lambda data: data["native_inboxes_after"][3].update(entries=[]))
        self.invalid(lambda data: data["native_inboxes_after_export"][3].update(entries=[]))

    def test_post_horizon_cargo_mutation_is_rejected(self):
        self.invalid(lambda data: data["native_actors_after_export"][0].update(cargo_wheat=1))

    def test_native_no_ai_cannot_disagree_with_runtime_in_both_snapshots(self):
        def mutate(data):
            data["native_actors_after"][0]["no_ai"] = False
            data["native_actors_after_export"][0]["no_ai"] = False
        self.invalid(mutate)

    def test_physical_output_not_inferred_from_message_or_selected_job(self):
        self.invalid(lambda data: data["inventories_after"]["destination"].update(wheat=1))

    def test_overflow_rejected_even_when_outputs_are_valid(self):
        self.invalid(lambda data: data["final"].update(record_capacity_denials=1))


class NativeEvidenceTests(unittest.TestCase):
    def test_real_binary_nbt_uuid_arrays_preserved(self):
        values = uuid_ints(identity("binary-uuid"))
        name = b"id"
        payload = b'\x0a\x00\x00\x0b' + struct.pack('>H', len(name)) + name + struct.pack('>i', 4)
        payload += struct.pack('>iiii', *values) + b'\x00'
        self.assertEqual(native_uuid(CommunicationNbtReader(payload).root()["id"]), identity("binary-uuid"))
        with self.assertRaises(ValueError): CommunicationNbtReader(payload[:-1]).root()

    def test_bounded_snbt_roundtrip_and_duplicate_key_rejection(self):
        data = one_send_fixture()
        witness = data["native_inboxes_after"][3]
        validate_inbox_witness(witness)
        self.assertEqual(len(witness["entries"]), 1)
        for text in ('{a:1,a:2}', '{a:NaN}', '{a:[I;1,2,3,4]} trailing', '[' + ','.join('1' for _ in range(17)) + ']'):
            with self.subTest(text=text), self.assertRaises(ValueError): SnbtReader(text).root()

    def test_unavailable_native_inbox_is_not_empty(self):
        class Missing:
            def run(self, command): return "No entity was found\n"
        with self.assertRaises(ValueError): inbox_witness(Missing(), actor_uuid(WORLD_SEED, 0))

    def test_duplicate_does_not_prune_expired_entries(self):
        data = one_send_fixture()["communication"]
        attempt = copy.deepcopy(data["attempts"][0])
        attempt.update(id=identity("duplicate"), tick=1000, outcome="DUPLICATE", reason="ALREADY_DELIVERED")
        data["attempts"].append(attempt)
        citizens = [actor_uuid(WORLD_SEED, slot) for slot in range(4)]
        inboxes, lifecycle = replay_inboxes(data, citizens, 1001)
        self.assertEqual(len(inboxes[citizens[3]]), 1)
        self.assertEqual(lifecycle[citizens[3]]["ttl_pruned"], 0)
        self.assertEqual(lifecycle[citizens[3]]["retained_expired_at_horizon"], 1)
        self.assertEqual(lifecycle[citizens[3]]["duplicate_without_pruning"], 1)

    def test_new_delivery_prunes_ttl_and_fifo_has_independent_counts(self):
        data = one_send_fixture()["communication"]
        original = copy.deepcopy(data["messages"][0]); original_attempt = copy.deepcopy(data["attempts"][0])
        for i in range(1, 18):
            message = dict(original, id=identity(f"message-{i}"), report_id=f"report-{i}",
                           sent_tick=680+i, delivered_tick=680+i, expires_after_tick=880+i)
            data["messages"].append(message)
            data["attempts"].append(dict(original_attempt, id=identity(f"attempt-{i}"), report_id=f"report-{i}", tick=680+i))
        citizens = [actor_uuid(WORLD_SEED, slot) for slot in range(4)]
        inboxes, lifecycle = replay_inboxes(data, citizens, 700)
        self.assertEqual(len(inboxes[citizens[3]]), 16)
        self.assertEqual(lifecycle[citizens[3]]["fifo_evicted"], 2)
        self.assertEqual(lifecycle[citizens[3]]["ttl_pruned"], 0)
        data["messages"].append(dict(original, id=identity("late-message"), report_id="late", sent_tick=1000,
                                     delivered_tick=1000, expires_after_tick=1200))
        data["attempts"].append(dict(original_attempt, id=identity("late-attempt"), report_id="late", tick=1000))
        inboxes, lifecycle = replay_inboxes(data, citizens, 1001)
        self.assertEqual(len(inboxes[citizens[3]]), 1)
        self.assertEqual(lifecycle[citizens[3]]["ttl_pruned"], 16)
        self.assertEqual(lifecycle[citizens[3]]["fifo_evicted"], 2)


class DeclarationAndDenominatorTests(unittest.TestCase):
    def test_duplicate_json_and_nonfinite_constants_rejected(self):
        for text in ('{"trial_id":"a","trial_id":"b"}', '{"value":NaN}', '{"value":Infinity}'):
            with self.subTest(text=text), self.assertRaises(ValueError): parse_json(text)

    def test_qualification_seeds_and_actors_cannot_be_expanded_study_slots(self):
        self.assertEqual(len(PLAN), 6)
        self.assertEqual({row["seed"] for row in PLAN}, {56101})
        self.assertEqual({row["policy_seed"] for row in PLAN}, {66104})
        for seed in (54101, 55101, 55124):
            with self.assertRaises(ValueError): actor_uuid(seed, 0)
        self.assertEqual(len({actor_uuid(WORLD_SEED, slot) for slot in range(4)}), 4)

    def test_six_valid_zero_outputs_do_not_grant_capability(self):
        rows = []
        for plan in PLAN:
            metrics = validate_trial(zero_output_fixture(plan["arm"]), WORLD_SEED, plan["arm"])
            rows.append(dict(plan, status="VALID_OBSERVATION", metrics=metrics,
                             capability=capability_coverage(plan["arm"], metrics)))
        result = qualification_summary(rows, [])
        self.assertEqual(result["valid_world_observations"], 6)
        self.assertTrue(result["all_planned_protocol_gates_passed"])
        self.assertFalse(result["qualification_gate_passed"])
        self.assertFalse(result["expanded_study_execution_authorized"])

    def test_missing_rows_never_become_zero_output_or_shrink_denominator(self):
        rows = [dict(plan, status="MISSING_ARTIFACTS", metrics=None, capability=None) for plan in PLAN]
        result = qualification_summary(rows, [])
        self.assertEqual(result["planned_worlds"], 6)
        self.assertEqual(result["invalid_or_missing_worlds"], 6)
        self.assertTrue(all(row["metrics"] is None for row in result["worlds"]))
        with self.assertRaises(ValueError): qualification_summary(rows[:-1], [])

    def test_plan_only_does_not_claim_dependency_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            plan = dict(PLAN[0], declaration_utc="2026-11-24T00:00:00+00:00")
            (directory / "planned-trial.json").write_text(json.dumps(plan))
            with patch('summarize_network_qualification.validate_plan'), patch('summarize_network_qualification.protocol_hash', return_value="hash"):
                result = summarize(directory, directory, "head", {"workflow": "wf", "run_id": "1", "run_attempt": "1"})
            self.assertEqual(result["worlds"][0]["status"], "NOT_RUN_BEFORE_RUNTIME")
            self.assertIsNone(result["worlds"][0]["metrics"])
            self.assertEqual(result["planned_worlds"], 6)

    def test_failed_malformed_identity_cannot_break_six_row_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            execution = {"workflow": "wf", "run_id": "1", "run_attempt": "1"}
            for index, malformed in enumerate((["not", "a", "uuid"], {"not": "a uuid"})):
                directory = root / PLAN[index]["trial_id"]; directory.mkdir()
                plan = dict(PLAN[index], declaration_utc="2026-11-24T00:00:00+00:00", source_commit="head",
                            source_tree="tree", protocol_sha256="protocol", initial_manifest_sha256="manifest",
                            execution_context=execution)
                result = dict(plan, schema=SCHEMA, status="INFRASTRUCTURE_FAILURE", github_run_id="1", github_run_attempt="1",
                              world={"world_uuid": malformed}, fixture={"final": {"episode": malformed}})
                (directory / "planned-trial.json").write_text(json.dumps(plan))
                (directory / "trial-result.json").write_text(json.dumps(result))
            with patch('summarize_network_qualification.validate_plan'), patch('summarize_network_qualification.protocol_hash', return_value="hash"):
                result = summarize(root, root, "head", execution)
            self.assertEqual(result["planned_worlds"], 6)
            self.assertEqual(len(result["worlds"]), 6)
            self.assertEqual([row["status"] for row in result["worlds"][:2]], ["INVALID_EVIDENCE"] * 2)
            self.assertTrue(all(row["metrics"] is None for row in result["worlds"]))
            self.assertTrue(all(row["world_uuid"] is None and row["episode"] is None for row in result["worlds"]))

    def test_failed_scope_and_unknown_status_are_not_trusted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            execution = {"workflow": "wf", "run_id": "1", "run_attempt": "1"}
            plan = dict(PLAN[0], declaration_utc="2026-11-24T00:00:00+00:00", source_commit="head",
                        source_tree="tree", protocol_sha256="protocol", initial_manifest_sha256="manifest",
                        execution_context=execution)
            (root / "planned-trial.json").write_text(json.dumps(plan))
            for changed in ({"status": "MADE_UP_SUCCESS"}, {"source_commit": "other-head"}, {"schema": "other-schema"}):
                result = dict(plan, schema=SCHEMA, status="INFRASTRUCTURE_FAILURE", github_run_id="1", github_run_attempt="1")
                result.update(changed)
                (root / "trial-result.json").write_text(json.dumps(result))
                with patch('summarize_network_qualification.validate_plan'), patch('summarize_network_qualification.protocol_hash', return_value="hash"):
                    summary = summarize(root, root, "head", execution)
                self.assertEqual(summary["worlds"][0]["status"], "INVALID_EVIDENCE")
                self.assertIsNone(summary["worlds"][0]["metrics"])

    def test_one_shot_reservation_survives_failure_before_world_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); output = root / "evidence"; output.mkdir()
            execution = {"workflow": "wf", "run_id": "1", "run_attempt": "1"}
            plan = dict(PLAN[0], declaration_utc="2026-11-24T00:00:00+00:00", source_commit="head",
                        source_tree="tree", protocol_sha256="protocol", initial_manifest_sha256="manifest",
                        execution_context=execution)
            (output / "planned-trial.json").write_text(json.dumps(plan))
            with patch.object(runner, 'plan_document', return_value=plan), patch.object(runner, 'context', return_value=execution), \
                 patch.object(runner, 'capture_build', side_effect=ValueError("no verified first build")), \
                 patch.object(runner.subprocess, 'Popen') as process:
                result = runner.run(root, plan["trial_id"], output)
                self.assertEqual(result["status"], "NOT_RUN_BEFORE_RUNTIME")
                self.assertFalse(result["fresh_world_directory"])
                self.assertIsNone(result["world"])
                process.assert_not_called()
                self.assertTrue((output / "world-attempt.json").exists())
                (output / "trial-result.json").unlink()
                with self.assertRaises(FileExistsError): runner.run(root, plan["trial_id"], output)


if __name__ == "__main__":
    unittest.main()
