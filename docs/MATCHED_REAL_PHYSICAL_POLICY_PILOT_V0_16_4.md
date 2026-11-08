# Hearthbound v0.16.4 — Matched physical policy pilot

## Objective

Compare the **same real Minecraft hauling motor** under two source-choice policies:

- **SCRIPTED**: highest-reported-wheat ranker from v0.16.1.
- **FROZEN_MLP**: simulator-supervised, SHA-256-pinned report-utility model from v0.16.2/3.

Both use actual recipient-owned reports communicated by a separate real scout, not live source inventories. Both dispatch through SableHauling.assign; both require the same executor provenance and independent source/destination inventory evidence.

All commands are permission-2 operator trials. An operator provides the candidate menu and destination but never supplies the source selected by the model. WITHHELD reads no recipient reports and must abstain without creating a job. The trial command is:

    /hearthbound-report-dispatch-trial <executor> <source-A> <source-B> <destination> <SCRIPTED|FROZEN_MLP> <EXPOSED|WITHHELD>

A successful assignment stores world identity, job UUID, actual executor, source report ID, source/destination, decision and assignment ticks, and policy/model identity on the real executor NBT. The read-only execution audit is still NOT independent inventory proof; actual source/destination deltas are checked separately.

## Pre-registered pilot design

Two held-out Minecraft seeds, one scenario each, and both policies per seed: **four independent disposable Forge server boots**.

| Seed | Scenario | A observed by scout | B observed by scout | Physical intervention before decision |
|---|---|---:|---:|---|
| 3101 | Fresh | 3 wheat | 1 wheat | None |
| 3102 | Unannounced depletion | 3 wheat | 1 wheat | A emptied after the scout delivers reports; executor receives no update |

Each arm has its own fresh server world with the same seed, source and destination geometry, scout/executor roles, and report protocol. No prior-arm cargo or claim can contaminate the comparison. This is an operator-defined matched intervention, not an observation given to either policy. Independent runner scheduling is NOT a randomized treatment order; do not claim it is.

The real trial requires: (1) executor initially unaware of source contents; (2) without a report, EXPOSED abstains; (3) scout directly observes actual Minecraft inventories and reports to Sable; (4) WITHHELD abstains with no job or physical mutation; (5) the policy makes one EXPOSED choice before work; (6) only the existing Minecraft motor hauls; (7) source decrement of one, destination increment of one, unused source unchanged, AND verified completed executor job are all required for success.

Attempts that pause, become quarantined or time out remain failed attempts. No teleport of a carrying executor or manual item transfer can turn a failure into success. Read-only motor and position diagnostics are retained.

## Pre-registered physical utility

- +1 for one verified physical item delivered after a completed executor job.
- -0.5 for an assigned job not physically completed with independent inventory evidence.
- 0 for an abstention with no job and no inventory mutation.

Report physical delivery rate, failed-assignment rate, abstention coverage, decision latency and successful-job server ticks separately, not only a scalar reward. The scalar is a deliberately limited pilot objective, NOT the actual colony reward contract.

The analyzer refuses invented successes, wrong inventory deltas, duplicate/missing matched arms, different model checksums and unauthorized reward/training side effects. It computes paired utility differences and a reproducible bootstrap interval by resampling whole seed pairs. With only two matched pairs the interval is **descriptive, not inferential** and cannot establish model superiority.

## Evidence and limitations

Workflow: .github/workflows/real-matched-physical-policy-pilot.yml

Trial: scripts/rcon_matched_physical_haul_trial.py

Analysis: scripts/analyze_matched_physical_hauls.py

Each independent worker trains the identical seed-fixed simulated model before Forge starts and verifies Python/Java frozen inference parity. The aggregate job requires four true Minecraft receipts, creates real-matched-physical-summary.json, and explicitly records that the sample is too small for a superiority claim.

Navigation regression #181 remains an ordinary failure mode, never a waived acceptance threshold. Persistent cargo/quarantine problems belong to an operator review, not silent retries.

The next stage, after this experiment passes, must increase the held-out world count, add counterbalanced or randomized treatment order, and test blocked routes, stale reports and source-claim conflicts. Do not award Create research discoveries, tech unlocks, social credit, personal reward, or neural gradients in the current pilot.

**Scientific scope:** verifying a fairer real Minecraft comparison of two already implemented policies; NOT establishing autonomous colony planning or reliable trained-policy advantage.
