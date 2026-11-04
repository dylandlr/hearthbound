# Hearthbound v0.12.5 — Finalized attention runs and restart integrity

This draft milestone is stacked on PR #145. The existing operator-opt-in Forge recorder writes a bounded JSONL hash chain of real citizen inspection decisions and their selected-source sensor outcomes. A **clean explicit stop** now creates a matching finalization manifest:

- `schema=hearthbound.attention-run-manifest.v1`
- `run_id` matches the JSONL filename and every record
- `records` matches the exact contiguous event count
- `final_hash` matches the last linked record
- `journal_sha256` matches every byte of the recorded JSONL file
- `finalized=true`, `action_authorized=false`

The manifest is first written to a fresh temporary file in the world save and atomically renamed to `attention-<run_id>.manifest.json`. A write/move failure returns `status=UNFINALIZED` and is reported by operator status. Interrupted and capped recordings do **not** receive a clean-stop manifest; they cannot silently pass the finalized-run verifier.

The independent Python verifier checks the original journal records, exact run/filename identity, complete file SHA-256, expected count, final chain digest and explicit finalization flag. Unit tests reject missing manifests, altered digests, forged counts, unfinalized flags and truncated tails.

## Real Forge restart acceptance

In both SCRIPTED and TRAINED_MLP dedicated-server CI trials, recording starts before two registered citizen source subscriptions are sampled. The RCON test explicitly stops recording. CI validates the actual world-save JSONL and finalized manifest **before** server restart. After Forge restarts from the saved world, CI validates the same files again and compares reports byte-for-byte. The manifest, journal, and both verification reports are archived in the experiment artifacts.

## Limits

This is **not** a cryptographic signature, remote attestation or guarantee against a hostile writer able to replace the journal and manifest together. Java's file append and temporary manifest write are not explicitly fsynced; abrupt power loss can still lose buffered records. A clean manifest only verifies the retained file's consistency, not all events that might have occurred before an interrupted stop. Filesystem reads and SHA-256 over the full file happen on the Forge command thread at stop; benchmark latency before long recordings. There is still no live neural policy or autonomous source registration.
