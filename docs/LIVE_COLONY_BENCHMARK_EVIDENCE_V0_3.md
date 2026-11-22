# Hearthbound v0.3 — Real four-citizen acceptance to aggregate benchmark evidence

This slice bridges **existing live Forge acceptance** to a machine-readable research observation. It does not modify gameplay, award research credit, train policies, or authenticate arbitrary uploaded logs.

## Actual world checks

`scripts/rcon_civilization_four_citizens.py` already independently demands:
- four physical source chests lose their original wheat,
- one destination chest actually contains exactly four wheat,
- zero outstanding source claims,
- zero held or assigned jobs,
- four distinct completed citizens,
- four scoped citizen decisions,
- disabled dispatcher at the end.

**Only after all of those pass** does the script print one `HEARTHBOUND_BENCHMARK_RECEIPT_V1` JSON line. The fields are aggregate physical evidence, not invented citizens or a synthetic trained policy.

`scripts/export-four-citizen-benchmark.js` reads the actual RCON log inside the same CI job and refuses absent, duplicate, out-of-order, malformed, contradictory, foreign-fixture, or inflated receipts. It requires an exact acceptance line, a numeric GitHub workflow run ID, and a full commit SHA; writes a no-overwrite JSON artifact; includes the SHA-256 of the captured log. This produces a **traceable attestation**, not a cryptographic proof of log authenticity, and the Python fixture string is not a durable Minecraft world UUID.

## MARBLE/PA4 scoring boundary

The single supported aggregate milestone is `four-independent-wheat-deliveries`, with one verified completed batch of four physical units. Individual agent UUIDs and per-job event IDs are not exported by this RCON test; the standalone verifier must therefore output `individualParticipation: null`, `messageEfficiency: null`, `learnedCooperation: null`, and `politicalEmergence: null`.

Do not feed the four citizens into a MARBLE-style `participationKpi` with invented identities. Do not classify one scripted fixture as a learned organization or count it as four independent experimental repetitions.

This is one scenario in one configured disposable Forge world. It cannot estimate variance, compare communication topologies, or establish a 100-agent society. Further matched-world benchmarking requires a world-bound journal adapter exporting authentic pre-action observations, citizen UUIDs, message delivery and per-job physical terminal outcomes.

## Reproduce

Pure contract:
```bash
node --check scripts/export-four-citizen-benchmark.js
node scripts/export-four-citizen-benchmark.test.js
```

The existing CI acceptance workflow `.github/workflows/real-four-citizen-colony.yml` additionally:
1. boots Forge and runs its existing real RCON test,
2. requires the physical success marker,
3. runs the exporter on `real-four-citizen-rcon.log`,
4. uploads `four-citizen-benchmark-evidence.json` with the world and RCON logs.

This remains a **read-only observer integration**. A successful parser unit test is not a live Forge result. Only completed, same-commit CI jobs and their artifact logs justify claiming end-to-end acceptance.
