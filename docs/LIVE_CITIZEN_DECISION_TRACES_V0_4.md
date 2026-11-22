# Live per-citizen decision-to-job trace v0.4

Research references: MARBLE / MultiAgentBench (ACL 2025), and CSCE 631 PA4 reading dossier P42, P06, P11, P32–33. Builds on PR #205's independently checked four-citizen physical production fixture.

## New read-only Forge command
Permission-2 `hearthbound-colony decision-traces` reads **only currently loaded** completed-task owners in the current server session. Each returned trace joins:

1. the persisted task id, current dimension's task/source/target and original physical haul job UUID;
2. the latest locally stored citizen decision UUID, evidence UUID and observation snapshot revision;
3. the matching current session episode UUID and decision policy identifier;
4. observed, decided, assigned and physically delivered game ticks;
5. the existing `SableHauling.completedJob` and `completedAssignment` gates.

A trace is omitted if the citizen is unloaded, latest memory is missing, the job was superseded, source positions disagree, the event is foreign, time chronology is invalid, or the action was not the declared scripted gather policy. The compact output uses a fixed 10-field record per task. It **does not** reconstruct old historical decisions for which only latest NBT remains, infer other agents' hidden observations, prove atomic crash recovery, or grant learning/reward authority.

## Live acceptance and exporter

`scripts/rcon_civilization_four_citizens.py` additionally requires four unique trace task IDs, citizen UUIDs, job UUIDs, decision UUIDs and evidence UUIDs, and validates observed ≤ decided ≤ assigned ≤ delivered ticks with the existing 20-tick source evidence age. It emits one `HEARTHBOUND_CITIZEN_TRACES_V1` record before the final success marker.

`scripts/export-four-citizen-benchmark.js` now refuses a benchmark artifact without that exact four-entry trace envelope. It stores entries alongside the previous aggregate inventory proof and the CI run/commit/log digest. The evidence score exposes **four verified citizen jobs**; a MARBLE-style individual participation rate remains null because there is still no exhaustive comparable per-agent/per-milestone ground-truth set spanning multiple independent benchmark tasks.

This is a current-session physically joined *scripted controller* baseline, **not evidence of learned occupation emergence, communication, political organization, or MARL policy advantage**. The plain text CI log is not cryptographically authenticated against hostile modification merely because it includes a digest.

## Validation
- Pure Java test: `python3 scripts/test-civilization-contracts.py` includes `ColonyDecisionTraceTest` and verifies episode, chronology, policy and freshness rejection.
- Node test: `node scripts/export-four-citizen-benchmark.test.js` requires distinct identities and rejects stale, invalid, duplicate and inflated receipts.
- Real acceptance: `.github/workflows/real-four-citizen-colony.yml` runs actual Forge with the original physical chest/claim checks, then verifies these traces and uploads a scoped JSON artifact.

A successful unit suite is not a successful live Forge run; inspect the exact commit's GitHub Actions logs and uploaded artifact before claiming end-to-end success.

## Next required integration
Capture decisions *before action* in an immutable world-bound journal, not solely latest citizen NBT. Join all terminal outcomes, including failures and uncertainty, to decision IDs. Then connect message provenance (sent / delivered / read) and the topology protocol to create true MARBLE-style collaboration metrics under matched Minecraft worlds, with scripted, untrained and frozen learned policy ablations.
