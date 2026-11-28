# QA #348: arrival at the native insertion boundary

Status: implementation, focused local contracts and independent review complete;
Java 17 / Forge compilation, the predeclared native suite, integration and ticket
acceptance remain open. Parent: [#227](https://github.com/dylandlr/hearthbound/issues/227).
Follow-up: [#348](https://github.com/dylandlr/hearthbound/issues/348).

## Failure evidence and uncertainty

The original failures remain failures. In [run 46090831824](https://github.com/dylandlr/hearthbound/actions/runs/46090831824),
source head `8206ca0e3bb6668e896ecb03d7bd1b0269ae7f50`,
[TRAINED_MLP baseline](https://github.com/dylandlr/hearthbound/actions/runs/46090831824/job/140811099525)
and [SCRIPTED resource-probe-A](https://github.com/dylandlr/hearthbound/actions/runs/46090831824/job/140811099560)
both booted Forge, confirmed Hearthbound and observed wheat counts source 8→7,
destination 0→1. Their subsequent 2.6-block proximity query failed, after two
and one transfer polls respectively. Those archives lack the insertion-time
pose and the failed-query pose. They cannot establish whether the delivery was
remote, the citizen moved after a valid delivery, or the geometries disagreed.

[SCRIPTED baseline](https://github.com/dylandlr/hearthbound/actions/runs/46090831824/job/140811099238)
failed before readiness at Gradle `:downloadAssets`, reporting that the horse
sound `minecraft/sounds/mob/horse/gallop3.ogg` could not be downloaded or validated.
The log does not separate transport from validation failure.
[TRAINED_MLP rapid-four-D](https://github.com/dylandlr/hearthbound/actions/runs/46090831824/job/140811099457)
also failed before readiness: the 12-minute readiness budget expired, with the
last Gradle tail through `:prepareRunServerCompile UP-TO-DATE`. That log does not
establish a narrower cause. Neither startup failure executed haul acceptance.
The completed matrix has seven passing slots and four failing slots; dependent
comparison jobs were skipped. No workflow was rerun to replace these outcomes.

The haul motor, controller, RCON smoke/diagnostic scripts and workflow on that
head were byte-identical to those at successful comparison head
`7cf3730e64433849c56952f88780284f8f98b2a0`
([run 46089616488](https://github.com/dylandlr/hearthbound/actions/runs/46089616488)).
That comparison narrows attribution; it does not diagnose harmless flakiness.
The furnace validator from #275 is not called by the failing haul path.

## Arrival contract and review decision

Arrival belongs to the insertion event for the exact assigned job. Inventory
movement and event-time position must both be witnessed. A later observation is
retained as its own fact. The design review approved this time boundary while
preserving **both existing geometries**:

| Requirement | Exact rule |
|---|---|
| Motor geometry | Squared distance from citizen feet to destination `(x+.5, y+.5, z+.5)` ≤ `6.25` |
| Smoke geometry | Squared distance from citizen feet to destination `(x+.5, y, z+.5)` ≤ `2.6 * 2.6` |
| Insertion samples | Both before and after positions satisfy both rules; no tolerance widens either radius |
| Material observations | Native local source chest remains 7 wheat; native destination chest changes 0→1 wheat across insertion |
| Existing RCON checks | The original destination Count=1 polling and source Count=7 assertion both pass |
| Query-time inventories | Source 7, destination 1, no other items in this controlled fixture |
| Identity | Same world UUID, server-session episode, dimension, citizen UUID, job UUID, assignment tick and exact endpoints throughout |
| Chronology | Assignment ≤ before insertion tick = after insertion tick = native delivered tick ≤ current query tick |
| Query order | Initial binding query tick ≤ final query tick; a fast insertion may precede the initial query |
| Later pose | Persisted and reported separately, including a later out-of-range query on an otherwise valid insertion |

The y centers differ by half a block. For example, `(7.5,103,1.5)` is exactly
2.5 blocks from the motor center but 3.0 blocks from the smoke center. This is a
geometry counterexample, not evidence that an archived failure had that pose.
The new validator rejects it. A citizen at `(6,100,1.5)` during insertion and
`(20,100,1.5)` later is distinguishable from a remote insertion followed by a
nearby later pose; only the first can satisfy event-time arrival.

## Implementation and authority boundaries

`HaulArrivalWitness` samples the actual citizen pose and native local container
NBT immediately around the existing insertion call on the server thread.
`HaulMotorDiagnostics.inventory` supplies the same bounded native NBT reader as
the existing diagnostic endpoint. It does not query an item capability, unpack
loot or make Create output assumptions. Capability-only, unloaded, partial,
malformed or otherwise unavailable inventories stay unavailable to this gate.
Chest-specific conservation checks live in the Python smoke validator, not in
the production motor.

The record binds the world identity and the existing `SourceReportSession`
episode at assignment. Inspection reads that fence without creating world
identity data. One record of at most 3,000 UTF-8 bytes lives on the current job;
a new assignment replaces that job record. The 3,900-byte RCON response limit
fails closed. A changed server session or job cannot reuse an old receipt.

Capture failures produce an unavailable observation. They do not retry the
motor, change navigation, cancel a job, grant credit, or change existing
insertion-exception/quarantine semantics. The existing `finally` observation
also records the physical state when the insertion call throws; a quarantined
job still fails the acceptance gate. The capture introduces no exactly-once,
crash-atomic or durable transaction claim. A persisted observation is not new
completion authority for production consumers.

`hearthbound-haul-arrival <citizen UUID>` is a permission-2 observation of the
exact loaded marked villager. It returns the insertion record separately from
current position, job phase, cargo presence and both current inventories. It
does not reconcile, move, freeze or repair the citizen. Native serialization
may invoke Minecraft/Forge serialization hooks; named citizen-NBT and position
invariants are checked, not a claim of whole-world purity.

The Python verifier independently recomputes distances from raw coordinates;
it does not trust a native `arrived` boolean, a phase label or an empty motor
return. It rejects missing, stale, foreign, malformed, duplicate-field and
nonfinite evidence. Source and destination observations must agree with the
specific chest fixture, including the destination's before value. The later
query uses the exact citizen UUID with the unchanged 2.6-block radius.

## Retained artifacts and independent replay

Each started smoke records `haul-arrival-evidence.json`, including exact checkout
and PR head when available, source hashes, GitHub run/attempt, matrix slot,
policy/seed/schedule/attention context, native assignment audit, all transfer
poll responses, source assertion, native UUID, raw insertion/current response
and later proximity response. On failure, the exact-citizen current snapshot,
pose, audit and endpoint inventory queries are retained, including read errors.
The artifact is uploaded by the existing `always()` upload step.

After the smoke passes, the workflow separately replays the raw records and
writes `haul-arrival-verified.json`:

```bash
python3 scripts/haul_arrival_evidence.py haul-arrival-evidence.json \
  --expected-checkout-sha "$(git rev-parse HEAD)"
```

Replay validates the original assignment, exact query identities, raw physical
poll sequence, source count and native insertion samples. Cached validation
booleans cannot substitute for those records. Artifacts still require ordinary
CI artifact digest/head verification; these JSON records are not signatures.

## Predeclared native trial set

Run the existing dedicated-server smoke matrix **once on the reviewed exact
head**, with no behavioral retries. Preserve the existing 75 polls × 2 seconds
(150-second haul budget), 12-minute startup budget, downstream scenarios and
all physical inventory checks. The matrix is unchanged:

| Slot | Policy | Configured seed | Resource schedule | Attention | Challenge |
|---|---|---|---|---|---|
| Baseline scripted | SCRIPTED | hearthbound-policy-v0-8-10 | baseline | scripted | none |
| Baseline trained | TRAINED_MLP | hearthbound-policy-v0-8-10 | baseline | scripted | none |
| A scripted | SCRIPTED | hearthbound-resource-probe-A | seeded-v1 | scripted | none |
| A trained | TRAINED_MLP | hearthbound-resource-probe-A | seeded-v1 | scripted | none |
| A neural attention | TRAINED_MLP | hearthbound-resource-probe-A | seeded-v1 | neural | none |
| B scripted | SCRIPTED | hearthbound-resource-probe-B | seeded-v1 | scripted | none |
| B neural attention | TRAINED_MLP | hearthbound-resource-probe-B | seeded-v1 | neural | none |
| C scripted | SCRIPTED | hearthbound-resource-probe-C | seeded-v1 | scripted | none |
| C neural attention | TRAINED_MLP | hearthbound-resource-probe-C | seeded-v1 | neural | none |
| D scripted rapid | SCRIPTED | hearthbound-rapid-four-D | baseline | scripted | rapid-four-v1 |
| D neural rapid | TRAINED_MLP | hearthbound-rapid-four-D | baseline | neural | rapid-four-v1 |

For this trial set use the matrix seeds, with no manual seed override. Report
all 11 attempted world slots, including startup failures, invalid witnesses,
physical failures and timeouts. Count independent world invocations, not
citizens; identical seed labels do not establish independent terrain samples.
The initial commanded wheat haul is not itself a learned-policy improvement
experiment. Later policy comparisons keep their existing gates and denominators.

## Focused validation and phase status

The focused Python contracts include valid delivery followed by later movement;
remote delivery followed by later arrival; the vertical-center mismatch;
both unchanged thresholds; stale world/session/job/citizen/endpoint/tick data;
missing or inconsistent native inventories; old destination stock; nonfinite
coordinates; malformed and duplicate JSON; corrupt RCON IDs; preservation of
failure diagnostics; and independent artifact replay. Synthetic fixtures are
explicitly transport-free and are not Minecraft runtime evidence.

Independent review also closed JSON floating-point aliases for all saved RCON
request/response IDs and regressing query chronology. The focused arrival suite
now has 24 passing tests. The 36 existing motor-diagnostic tests and the prior
hauling poll/framing contracts also passed locally.

The standalone Java contract checks the actual geometry helper, including
distinct event/later poses, the center mismatch and nonfinite/overflow inputs.
Local execution used OpenJDK 21.0.13.1; Java 17 compilation is a CI gate. The
native bridge has not yet been compiled or executed in Forge for this change.

```bash
python3 -m unittest discover -s scripts -p test_haul_arrival_evidence.py -v
python3 scripts/test_haul_smoke_diagnostics.py
python3 scripts/test_haul_smoke_simulated_rcon.py
python3 scripts/test_rcon_frames.py
javac --release 17 -d /tmp/hb-arrival-contract \
  src/main/java/dev/hearthbound/evidence/HaulArrivalGeometry.java \
  src/test/java/dev/hearthbound/evidence/HaulArrivalGeometryTest.java
java -cp /tmp/hb-arrival-contract dev.hearthbound.evidence.HaulArrivalGeometryTest
```

Requirements, technical design, test design, implementation and independent review
are complete for this bounded repair. All 24 focused arrival tests passed, including
review corrections for integer response identities and query chronology. Local QA
also retained the existing motor, polling and framing checks. Java 17/Forge compilation
and all native slots remain required before acceptance.
The historical cause remains unresolved; only newly captured event-time data
can classify the next observations. No original failure is retroactively passed.

## Relevant references

This work applies the repository `AGENTS.md` evidence rule separating accepted
actions from independently observed world change, the existing diagnostic
contract, and the exact issue/source/CI evidence above. The implementation
changes an arrival evidence boundary, not an AI learning result. Unrelated
research findings are not added to this routine RCON/QA repair.
