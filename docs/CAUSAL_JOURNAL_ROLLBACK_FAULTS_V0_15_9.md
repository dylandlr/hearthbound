# Hearthbound v0.15.9 — Adversarial causal-journal recovery

This milestone is a **test harness and recovery validation**, not a reward or learning system.

## Standalone byte-interruption tests

`CausalEvidenceJournalFaultTest` builds a valid world-bound, multi-event journal and cuts it after every possible byte offset. It requires all partially written frame headers and payloads to fail closed. It accepts structurally complete prefixes only as *historical records*: recovered `ADMITTED` entries must report `activeForAudit=false` until freshly checked against live evidence.

The suite also verifies independent event isolation, terminal revocation, foreign-world UUID rejection, valid CRC32 with an inconsistent SHA-256 sequence chain, and explicit source-mismatch revocation after reopening an old journal snapshot.

**Limitation:** A perfectly intact earlier prefix is indistinguishable from a genuine older journal without an external monotonic anchor. The implementation never treats a recovered admission as authority to pay rewards. An adversary able to rewrite the entire file and recompute an unkeyed hash chain is outside the journal's integrity guarantees.

## Real Forge/Create partial-save rollback

`.github/workflows/real-causal-rollback.yml` launches the *same* Minecraft/Forge/Create world three times:

1. **Baseline:** establish the world UUID and an empty journal without creating any physical Create callback. Save and shut down.
2. **Experiment:** command a real villager to haul wheat into the powered Create millstone, observe the actual `process()` callback, and write an fsynced `ADMITTED` causal audit event. Save and shut down.
3. **Fault:** while the server is offline, restore only the Create callback SavedData to its baseline (absent) state. Preserve the world UUID, citizen NBT, and causal journal. Reboot and run a live evidence check. The original journal record must change to **`REVOKED`** and must never be used to credit research.

This is a deliberately engineered **partial-world rollback**, not an arbitrary full-world rewind, power cut, or byzantine attack. Its purpose is to reveal unsafe assumptions of atomicity between a Minecraft SavedData receipt and an independent fsynced log. A separate full-checkpoint rollback test requires an external version fence; restoring both world and journal to a common old prefix is not provably detectable from those files alone.

## No reward delivery

`ADMITTED` is an audit state only. No `DurableRewardLedger.credit`, research inbox drain, recipe unlock, or model update may occur here. Failing to find a physical callback after rollback must cause permanent revocation, not a compensating invented source record.

## Existing failure tracked independently

One existing large dedicated-server matrix run had Sable carrying wheat but failing to reach a chest within its timeout. That is a **navigation regression**; do not relax the final delivery requirements to hide it. Keep that issue separate from causal journal integrity and reproduce with movement/obstacle logs.
