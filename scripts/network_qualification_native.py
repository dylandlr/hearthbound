#!/usr/bin/env python3
"""Bounded native inbox witnesses and saved communication-history comparisons."""
import gzip
import hashlib
import json
import re
import struct
from uuid import UUID

from rcon_private_communication_trial import packed, require, uuid
from run_colony_reliability_trial import NbtReader


class CommunicationNbtReader(NbtReader):
    """The legacy level reader intentionally discards arrays; UUIDs need them."""
    def value(self, kind, depth=0):
        if kind == 11:
            require(depth <= 64, "Excessive communication NBT nesting")
            count = self.number("i")
            require(0 <= count <= 4096, "Oversized communication integer array")
            return list(struct.unpack(">" + "i" * count, self.take(count * 4)))
        return super().value(kind, depth)


class SnbtReader:
    """Only the compound/list/string/integer subset used by the native inbox."""
    def __init__(self, text):
        require(isinstance(text, str) and len(text.encode()) <= 262144, "Oversized native inbox")
        self.text, self.offset, self.nodes = text, 0, 0

    def whitespace(self):
        while self.offset < len(self.text) and self.text[self.offset].isspace():
            self.offset += 1

    def take(self, token):
        self.whitespace()
        require(self.text.startswith(token, self.offset), "Malformed native inbox SNBT")
        self.offset += len(token)

    def quoted(self):
        self.whitespace()
        require(self.offset < len(self.text) and self.text[self.offset] == '"', "Expected quoted native value")
        value, end = json.JSONDecoder().raw_decode(self.text[self.offset:])
        require(isinstance(value, str), "Native string type changed")
        self.offset += end
        return value

    def value(self, depth=0):
        self.whitespace()
        self.nodes += 1
        require(depth <= 8 and self.nodes <= 4096 and self.offset < len(self.text), "Native inbox parse bound exceeded")
        token = self.text[self.offset]
        if token == '"':
            return self.quoted()
        if token == '{':
            self.take('{'); result = {}
            self.whitespace()
            if self.text.startswith('}', self.offset):
                self.take('}'); return result
            while True:
                self.whitespace()
                if self.text.startswith('"', self.offset):
                    key = self.quoted()
                else:
                    found = re.match(r'[A-Za-z0-9_.+-]+', self.text[self.offset:])
                    require(found is not None, "Malformed native inbox key")
                    key = found.group(); self.offset += len(key)
                require(key not in result, "Duplicate native inbox field")
                self.take(':'); result[key] = self.value(depth + 1)
                self.whitespace()
                if self.text.startswith('}', self.offset):
                    self.take('}'); return result
                self.take(',')
        if token == '[':
            self.take('['); self.whitespace(); integer_array = False
            if self.text.startswith('I;', self.offset):
                self.take('I;'); integer_array = True
            result = []; self.whitespace()
            if self.text.startswith(']', self.offset):
                self.take(']'); return result
            while True:
                item = self.value(depth + 1)
                require(not integer_array or type(item) is int, "Native UUID array type changed")
                result.append(item)
                require(len(result) <= 16, "Native inbox list exceeds capacity")
                self.whitespace()
                if self.text.startswith(']', self.offset):
                    self.take(']'); return result
                self.take(',')
        found = re.match(r'-?\d+[bBsSlL]?(?=\s*[,}\]])', self.text[self.offset:])
        require(found is not None, "Unsupported native inbox value")
        self.offset += len(found.group())
        return int(found.group().rstrip('bBsSlL'))

    def root(self):
        value = self.value()
        self.whitespace()
        require(self.offset == len(self.text), "Trailing native inbox data")
        return value


def native_uuid(value):
    require(isinstance(value, list) and len(value) == 4
            and all(type(item) is int and -(2 ** 31) <= item < 2 ** 31 for item in value),
            "Invalid native UUID array")
    return str(UUID(bytes=struct.pack('>iiii', *value)))


def normalize_inbox(root):
    require(type(root) is dict and set(root) == {"schema", "entries"}
            and root["schema"] == "hearthbound.citizen-reports.v1"
            and isinstance(root["entries"], list) and len(root["entries"]) <= 16,
            "Native inbox schema or bound changed")
    keys = {"observationWorld", "observationSession", "id", "source", "state", "wheat",
            "observed_tick", "delivered_tick", "source_revision", "sender", "recipient", "origin"}
    rows = []
    for report in root["entries"]:
        require(type(report) is dict and set(report) == keys, "Native report fields changed")
        row = dict(report)
        for key in ("observationWorld", "observationSession", "sender", "recipient"):
            row[key] = native_uuid(row[key])
        require(all(type(row[key]) is int for key in ("wheat", "observed_tick", "delivered_tick", "source_revision"))
                and all(isinstance(row[key], str) for key in keys - {"wheat", "observed_tick", "delivered_tick", "source_revision"}),
                "Native report field type changed")
        rows.append(row)
    require(len({row["id"] for row in rows}) == len(rows), "Duplicate reports in native inbox")
    return rows


def inbox_witness(rcon, citizen):
    path = 'ForgeData."hearthbound.citizen_reports.v1"'
    existence = rcon.run(f'execute if data entity {citizen} {path}')
    if existence.strip() == 'Test failed':
        return {"citizen": citizen, "status": "ABSENT_AT_NATIVE_PROBE", "presence_raw": existence,
                "raw": None, "entries": []}
    require(existence.strip() == 'Test passed, count: 1', "Native inbox unavailable; absence not established")
    raw = rcon.require(f'data get entity {citizen} {path}', 'entity data:')
    entries = normalize_inbox(SnbtReader(raw.split('entity data:', 1)[1].strip()).root())
    return {"citizen": citizen, "status": "OBSERVED_NATIVE_INBOX", "presence_raw": existence,
            "raw": raw, "entries": entries}


def validate_inbox_witness(witness):
    if witness["status"] == "ABSENT_AT_NATIVE_PROBE":
        require(witness["presence_raw"].strip() == 'Test failed'
                and witness["raw"] is None and witness["entries"] == [], "Native absence witness changed")
    else:
        require(witness["status"] == "OBSERVED_NATIVE_INBOX"
                and witness["presence_raw"].strip() == 'Test passed, count: 1', "Invalid native inbox status")
        parsed = normalize_inbox(SnbtReader(witness["raw"].split('entity data:', 1)[1].strip()).root())
        require(parsed == witness["entries"], "Native inbox differs from raw witness")


def derive_episode(world, observation_session, dimension):
    """Exact Java UUID.nameUUIDFromBytes(world|rawSession|dimension), UTF-8.

    This hashes the bytes directly. Python uuid3(namespace, name) would prepend
    namespace bytes and produce a different identifier.
    """
    uuid(world); uuid(observation_session)
    require(isinstance(dimension, str) and re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_/.-]+", dimension),
            "Invalid episode dimension")
    encoded = (world + "|" + observation_session + "|" + dimension).encode("utf-8")
    return str(UUID(bytes=hashlib.md5(encoded, usedforsecurity=False).digest(), version=3))


def native_report_id(message, observation_session):
    """The exact transport identity includes the raw observation session."""
    uuid(message["sender"]); uuid(message["world"]); uuid(observation_session)
    require(isinstance(message["source"], str) and type(message["source_revision"]) is int
            and message["source_revision"] > 0 and type(message["observed_tick"]) is int,
            "Invalid native report identity fields")
    return (message["sender"] + "|" + message["source"] + "|" + str(message["source_revision"])
            + "|" + str(message["observed_tick"]) + "|" + message["world"] + "|" + observation_session)


def expected_report(message, observation_session, dimension):
    require(derive_episode(message["world"], observation_session, dimension) == uuid(message["episode"]),
            "Raw observation session does not derive the scoped message episode")
    require(message["source"].split("|", 1)[0] == dimension
            and message["report_id"] == native_report_id(message, observation_session),
            "Native report identity differs from exact observation provenance")
    return {"observationWorld": message["world"], "observationSession": observation_session,
            "id": message["report_id"], "source": message["source"],
            "state": "AVAILABLE" if message["reported_wheat"] > 0 else "EMPTY",
            "wheat": message["reported_wheat"], "observed_tick": message["observed_tick"],
            "delivered_tick": message["delivered_tick"], "source_revision": message["source_revision"],
            "sender": message["sender"], "recipient": message["recipient"],
            "origin": "REPORTED_DIRECT_FORGE_OBSERVATION"}


def replay_inboxes(communication, citizens, end_tick, message_sessions, dimension):
    require(isinstance(message_sessions, dict)
            and set(message_sessions) == {message["id"] for message in communication["messages"]},
            "Raw session mapping must cover exactly the actually delivered messages")
    inboxes = {citizen: [] for citizen in citizens}
    counters = {citizen: {"ttl_pruned": 0, "fifo_evicted": 0, "duplicate_without_pruning": 0}
                for citizen in citizens}
    for attempt in communication["attempts"]:
        recipient = attempt["recipient"]; current = inboxes[recipient]
        if attempt["outcome"] == "REJECTED":
            continue
        duplicates = [row for row in current if row["id"] == attempt["report_id"]]
        if attempt["outcome"] == "DUPLICATE":
            require(len(duplicates) == 1, "Duplicate attempt has no retained original inbox report")
            counters[recipient]["duplicate_without_pruning"] += 1
            continue
        require(attempt["outcome"] == "DELIVERED" and not duplicates, "New delivery duplicated retained report")
        messages = [message for message in communication["messages"]
                    if message["report_id"] == attempt["report_id"] and message["recipient"] == recipient]
        require(len(messages) == 1, "Delivered attempt has ambiguous message")
        retained = [row for row in current if 0 <= attempt["tick"] - row["delivered_tick"] <= 200]
        counters[recipient]["ttl_pruned"] += len(current) - len(retained)
        while len(retained) >= 16:
            retained.pop(0); counters[recipient]["fifo_evicted"] += 1
        message = messages[0]
        retained.append(expected_report(message, message_sessions[message["id"]], dimension)); inboxes[recipient] = retained
    for citizen, entries in inboxes.items():
        counters[citizen]["retained"] = len(entries)
        counters[citizen]["retained_expired_at_horizon"] = sum(end_tick - row["delivered_tick"] > 200 for row in entries)
    return inboxes, counters


def verify_native_history(path, exported, runtime_records):
    saved = CommunicationNbtReader(gzip.decompress(path.read_bytes())).root()["data"]
    require(saved["schema"] == "hearthbound.citizen-communication.v1"
            and "invalidSavedHistory" not in saved, "Native communication schema/quarantine mismatch")
    messages = []
    for row in saved["messages"]:
        message = {key: native_uuid(row[key]) for key in ("id", "world", "episode", "sender", "recipient")}
        for source, target in (("reportId", "report_id"), ("source", "source"), ("wheat", "reported_wheat"),
                               ("sourceRevision", "source_revision"), ("observed", "observed_tick"),
                               ("sent", "sent_tick"), ("delivered", "delivered_tick")):
            message[target] = row[source]
        message.update(expires_after_tick=message["delivered_tick"] + 200, transport="EXPLICIT_LOCAL_SYNCHRONOUS")
        messages.append(message)
    require(messages == exported["messages"], "Native message history differs from exported evidence")
    attempts = []
    for row in saved["sendRecords"]:
        attempt = {key: native_uuid(row[key]) for key in ("id", "world", "episode", "sender", "recipient")}
        attempt.update({key: row[key] for key in ("source", "outcome", "reason", "tick")})
        if "reportId" in row:
            attempt["report_id"] = row["reportId"]
        attempts.append(attempt)
    require(attempts == exported["attempts"], "Native attempt history differs from exported evidence")
    jobs = {native_uuid(row["job"]): row for row in saved["jobs"]}
    require(len(jobs) == len(saved["jobs"]), "Duplicate native job binding")
    events = []
    for row in saved["events"]:
        event = {"sequence": row["sequence"], "stage": row["stage"], "message_id": native_uuid(row["message"]),
                 "actor": native_uuid(row["actor"]), "tick": row["tick"]}
        if "decision" in row:
            event["decision_id"] = native_uuid(row["decision"])
        if "job" in row:
            event["job_id"] = native_uuid(row["job"])
            binding = jobs[event["job_id"]]
            position = binding["destination"]
            x, z, y = position >> 38, (position >> 12) & 0x3ffffff, position & 0xfff
            if z >= 2 ** 25: z -= 2 ** 26
            if y >= 2 ** 11: y -= 2 ** 12
            event["destination"] = f"minecraft:overworld|{x},{y},{z}"
        if row["stage"] == "PHYSICAL_COMPLETED":
            event.update(wheat_transferred=1, witness="EXECUTOR_INSERTION_RETURNED_NO_REMAINDER")
        events.append(event)
    require(events == exported["events"], "Native lifecycle history differs from exported evidence")
    assigned = {row["job"]: row for row in runtime_records
                if row["kind"] == "ASSIGNED" and row["mode"] == "REPORT_CUED_DIRECT_RECHECK"}
    require(set(assigned) == set(jobs), "Native job bindings differ from report-cued assignments")
    for job, binding in jobs.items():
        assignment = assigned[job]
        require(native_uuid(binding["citizen"]) == assignment["citizen"]
                and native_uuid(binding["decision"]) == assignment["decision"]
                and binding["source"] == packed(assignment["source"])
                and binding["destination"] == packed(assignment["destination"])
                and binding["assigned"] == assignment["assigned_tick"], "Native job authority binding changed")
        matching = [event for event in events if event["stage"] == "ASSIGNED" and event["job_id"] == job]
        require(len(matching) == 1 and matching[0]["message_id"] == native_uuid(binding["message"]),
                "Native job changed selected message")
    for native, audit in (("capacityDenials", "capacity_denials"), ("sendAttempts", "send_attempts"),
                           ("rejectedSends", "rejected_sends"), ("duplicateSends", "duplicate_sends"),
                           ("recordingErrors", "recording_errors"), ("attemptCapacityDenials", "attempt_capacity_denials")):
        require(saved[native] == exported["audit"][audit], "Native journal counter mismatch")
    return {"native_messages": len(messages), "native_attempts": len(attempts),
            "native_events": len(events), "native_job_bindings": len(jobs)}
