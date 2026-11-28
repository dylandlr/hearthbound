# C14-02 crop failure: proposed requirements, design, and test plan

Parent: [C14-02 / #323](https://github.com/dylandlr/hearthbound/issues/323).
**Status: proposed; independent review completed with implementation blockers retained.** This document advances requirements,
design, and test design only. No crop adapter, native witness, fixture runner, or binding protocol
described here has been implemented or executed. All implementation, CI, native validation, learning,
integration, and acceptance phases remain **not run** for C14-02.

## 1. Original requirement and acceptance, unchanged

**Original scope:** `Reduce crop yield or destroy selected crops`

**Original acceptance:** `Actual harvest loss measured; paired control unchanged`

The proposed first version implements the destruction alternative: remove a deterministic fraction
of explicitly selected mature wheat at START, without producing harvest items. A later real harvest
must establish the resulting loss. Counting missing blocks, issuing an injection command, or receiving
a scheduler APPLIED receipt cannot by itself satisfy the acceptance criterion.

END is non-restorative: it ends the scheduled interval and releases an established adapter reservation
only when the native context is settled. It never restores crops, seeds, inventories, cargo, or rewards.
There is no automatic replanting, recovery policy, citizen reassignment, curriculum change, or actor
observation injected by the adapter.

Independent review on 27 November 2026 (America/Chicago) confirmed the original acceptance wording,
the examined native harvest/observation behavior, paired ranking and yield expectations, and the
separation between planned tests and executed evidence. It clarified no-event ownership and the
information-flow oracle below. It did not approve the unresolved native-context publication,
durability, hook-ordering or witness contracts for implementation.

## 2. Pinned basis and dependencies

| Basis | Pinned source and meaning |
| --- | --- |
| Native behavior examined | Historical v0.23 candidate `a072519518db1458e8cb5aa1898aebd4ba93f03a`; see the [baseline artifact audit](C00_BASELINE_ARTIFACT_AUDIT.md). This is a candidate, not an integrated release. |
| Durable delivery | [PR #234](https://github.com/dylandlr/hearthbound/pull/234), head `7cf3730e64433849c56952f88780284f8f98b2a0`; [scheduler-v2 contract](https://github.com/dylandlr/hearthbound/blob/7cf3730e64433849c56952f88780284f8f98b2a0/docs/C14_EVENT_SCHEDULER_CONTRACT.md). |
| Seeded planning and configured targets | [PR #352](https://github.com/dylandlr/hearthbound/pull/352), head `59772fbacd0cb0d056b29b70b96c91bc8f5cce6e`; [scenario-v1 contract](https://github.com/dylandlr/hearthbound/blob/59772fbacd0cb0d056b29b70b96c91bc8f5cce6e/docs/C14_SEEDED_SCENARIO_CONTRACT.md). |
| Relevant research record | [C14_EVENT_SCHEDULER_REFERENCES.md at the scenario head](https://github.com/dylandlr/hearthbound/blob/59772fbacd0cb0d056b29b70b96c91bc8f5cce6e/docs/C14_EVENT_SCHEDULER_REFERENCES.md); applications and exact prior reading locations appear in section 10. |

The two native classes examined below have identical bytes at the baseline and scenario heads.
`VillageWorkActions.java` has SHA-256
`322ef1345929baf87d366b78e7f1952d59d0b95ea226dc45659040f1a5747853`;
`VillageEconomyRuntime.java` has SHA-256
`311cc80cba853c7e9342dfc1110664f45a6349cd3262f3f8642f7fc192b47370`.
This source comparison does not integrate either draft PR or validate a new native adapter.

Dependency refinement preserves the original **C03 multiagent-learning epic dependency**. The
scheduler and scenario contracts are prerequisites for adapter execution; independent native
observations and custody checks are prerequisites for physical acceptance. C03 remains a later
adaptation/integration dependency, including policy provenance and independent-world evaluation.
A successful no-agent physical fixture would neither satisfy C03 nor remove that dependency.
Baseline selection and the relevant existing native regression gates also remain separate.

## 3. Existing native behavior constrains this design

[`VillageWorkActions.farm`](https://github.com/dylandlr/hearthbound/blob/a072519518db1458e8cb5aa1898aebd4ba93f03a/src/main/java/dev/hearthbound/world/VillageWorkActions.java)
checks mature wheat, obtains one real replanting seed from the depot, then checks wheat maturity and
farmland again at the crop. It calls native `Block.getDrops` with the actor and an empty tool, accepts
only wheat/seeds, and requires exactly one wheat. It removes the crop to air, transfers those native
drops directly into owned cargo, consumes one seed, replants wheat at age zero, and later delivers
the cargo. This path does not spawn its harvest as dropped item entities. When the crop has changed
before the crop phase, the unused seed is returned; unresolved custody prevents normal settlement.

The adapter must not call this authored farming skill as its disruption, consume its seed, forge its
harvest witness, or clear its leases/cargo. A no-drop crop deletion and an ordinary productive harvest
have different material effects. The six-world fixture below uses a separate real native break/drop
operation for measurement, with no village worker; therefore its item-entity count must not be
mistaken for how the existing village harvest skill transports output.

[`VillageEconomyRuntime.sense`, `known`, `menu`, and `tick`](https://github.com/dylandlr/hearthbound/blob/a072519518db1458e8cb5aa1898aebd4ba93f03a/src/main/java/dev/hearthbound/world/VillageEconomyRuntime.java)
obtain local facts from loaded native positions within sensor distance 16. Crop facts contain the
observed mature flag; other facts contain observed inventory/water state. Fact validity uses a
600-tick lifetime; sensing/work dispatch runs through the citizen's existing 20-tick cadence.
Work offers use those private facts, and local exchanges convey facts rather than an experiment
schedule. These observations can become stale. The adapter must not patch the books, manufacture a
new fact, refresh a fact early, or expose planned event times. Later citizens may learn about an actual
missing crop through their existing sensing and communication interfaces only. That integration
requires its own test; the no-agent fixture cannot establish it.

## 4. Proposed bounded adapter contract

### Admission and modes

Native version `crop-destruction-v1` admits one latent `crop_failure` choice per trial, one dimension,
and 1–32 explicit candidate positions from that choice. Extra choices/kinds are rejected at admission;
this is a bounded first physical slice, not support for every schedule the generic scheduler accepts.
The permitted box must have each axis at most 16 blocks and volume at most 512 blocks. The separately
declared one-block observation/neighbor guard must stay within a 4096-block cap. These native limits
are deliberately stricter than scenario-v1's logical-coordinate limits.

| Mode | START behavior | END behavior | Measurement |
| --- | --- | --- | --- |
| Treatment | Preflight all candidates; destroy the ranked subset using a no-drop native mutation; independently verify the result. | Non-restorative lifecycle completion only. | Measure surviving crops through a real native harvest. |
| Sham | Same intended subset calculation, preflight, timing, reservation and instrumentation; perform no block/inventory/entity mutation. | Same non-restorative completion. | Same harvest and independent output capture. |
| No-event | Preserve the latent choice and context binding; the scenario schedule contains no events. No fake START/END or effect receipt is manufactured. | No transition exists. | The observer visits the same absolute measurement boundaries and performs the same later harvest. |

Sham is an explicit adapter mode, not merely an inference from a zero binary64 severity. Mode,
intended ppm, effective severity, and event identity must agree with the regenerated scenario manifest.
The native adapter uses the integer intended ppm and verifies its correspondence to the emitted
event; it does not reconstruct ppm by approximately rounding an arbitrary supplied double.

All three nominal arms have an exclusively registered fixture footprint from setup through final
harvest verification. This experiment-registration ownership is distinct from an adapter transition
reservation. The no-event observer remains read-only and creates neither a transition reservation
nor an effect receipt. Treatment/sham transition reservations cannot release the enclosing fixture's
ownership early. Live-colony reservation effects need separate validation; this no-agent fixture
cannot establish that reservations are behaviorally neutral.

### Severity and paired subset

Let `N` be the number of explicit candidates in `Choice.targets`, not all crops found in the region,
and let `p` be intended severity in integer ppm. Define `k = floor(N * p / 1000000)` using checked
integer arithmetic. Preflight failure never shrinks N, chooses replacement crops, or reranks survivors.

For each canonical position `(x,y,z)`, compute SHA-256 over these exact ASCII bytes:

```text
hearthbound:crop-subset:v1<LF>
<pair_id><LF>
<scope_sha256><LF>
<target_sha256><LF>
<x><TAB><y><TAB><z><LF>
```

`<LF>` and `<TAB>` denote the actual characters. Coordinates use canonical signed decimals. Rank
ascending by the unsigned digest bytes, then numeric `(x,y,z)` as the deterministic tie-breaker; select
the first k positions. Mutation order is numeric `(x,y,z)` within that selected set. The ranking uses
the mode-independent scenario `pair_id`, never mode, trial ID, world ID, or mode-specific event ID.
Thus the paired arms share an intended subset; their physical worlds and outcomes remain separate.

For N=8: ppm 0 and 124999 select zero, 125000 selects one, 500000 selects four, 999999 selects seven,
and 1000000 selects eight. A positive severity that rounds to zero is an explicitly recorded verified
no-op, not evidence of harvest loss. Sham applies zero mutations while retaining its counterfactual
k/subset. No-event retains the same planned information privately without dispatching an operation.
Different seeds need not select different subsets by chance; tests require reproducibility and
correct specified ranking, not a false universal uniqueness guarantee.

### Identities and the native context binding: review blocker

Retain the real persistent world UUID obtained from `HearthboundWorldIdentity` for the actual
`ServerLevel`, the dimension, original trial ID, scenario manifest/hash, scenario-derived journal run
ID, schedule hash, event ID, phase, pair ID, scope/target hashes, and native adapter version. Use the
existing scenario create/open wrappers unchanged. Do not derive an arbitrary replacement world ID,
change their run-ID formula, or modify scheduler-v2 journal semantics for this feature.

The additional immutable native context must bind adapter operation/version, ranking and rounding
rules, native limits, declared preconditions/guard, clock boundaries, fixture/environment and
loot-resource versions, and measurement protocol. Its hash must be computed from a reviewed canonical
encoding and checked against a **durably preregistered expected digest independent of the sidecar**.
A proposed second binding is an experiment registration/SavedData marker keyed by the real world UUID
and the scenario-derived run ID, also recorded in the frozen cohort registration. The expected digest
must not simply be recalculated from whichever sidecar happens to exist on reopen.

Proposed creation sequence: establish an INCOMPLETE registration with expected bindings; durably
publish the sidecar by exclusive creation; create the scheduler through the scenario wrapper; verify
both bindings and the journal identity; publish/read back a READY registration. No physical mutation
is allowed during creation. Open must first validate the preregistered digest, independent world
marker, sidecar bytes, and complete creation state, then open the bound scheduler. A changed adapter,
precondition, or measurement field fails before opening/mutating, including for an empty control.
Missing, partially created, conflicting, or rolled-back bindings are retained as invalid/held trials;
they are not silently recreated, migrated, deleted, or accepted as a new run.

**This sequence is a proposal, not a solved atomic transaction across files and world saves.** Review
must specify the exact byte encoding, marker persistence/flush evidence, exclusive ownership,
creation failure states, rollback detection, and reopen rules before implementation. A SavedData dirty
flag alone is not proof of durable registration. If those guarantees cannot be established, native
execution remains blocked. Matching hashes provide consistency, not authentication against wholesale
evidence replacement.

## 5. Native execution and failure semantics

### All-target preflight at the scheduled START tick

Use one reviewed server-level tick hook and the actual `ServerLevel.getGameTime()` value. The proposed
hook is the level's END tick phase, with a tested once-per-level-per-tick ordering. All world reads
and mutations run on the authoritative server thread. No client callback, wall clock, day-time value,
relative-tick translation, chunk-loading retry, or background thread may execute the shock.

Before any mutation, validate all of the following and capture an independent before observation:

1. The live world/dimension and frozen native context match; the scheduler's current pending START
   is exactly the expected bound transition, executable at the current native tick, and not a held
   restart or a previously attempted/settled dispatch. Reserve the context against duplicate dispatch.
2. Raw coordinates satisfy the actual dimension's build-height and world-border constraints before
   any packed-position conversion; round-trip conversion must preserve every coordinate. The whole
   permitted/guard footprint and all selected crops/supports are already loaded. Checking must not
   generate or force-load chunks, or fall back to another dimension.
3. Every candidate is inside the declared box, is explicitly listed once, is `minecraft:wheat` at
   maximum age, and has native farmland immediately beneath it. Both crop and support are within the
   authorized fixture footprint. There are no target block entities. Capture full relevant block
   properties, not only the mature flag. Reject wrong/immature/missing crops or changed support.
4. The before state agrees with the registered fixture/preconditions. No incompatible active crop
   lease, owned farm action, overlapping experiment reservation, unexplained item entity, or external
   producer is present. Acquire all candidate reservations, including the unmutated candidates and
   controls. Reject conflicts; do not cancel citizen work or wait for a later tick.
5. The independent observer is available, storage/evidence capacity is reserved, and before counts
   for native item entities and all relevant containers/cargo are captured. The plan, configured
   target digest and a separately hashed observed-state snapshot must remain distinct fields.

For the first fixture there are no citizens or active economic work. Custody conflicts are separate
adversarial tests. They are not silently removed from future live-colony deployments.
For no-event controls, the observer performs the same physical precondition checks and captures at
the same ticks; the pending-transition eligibility check and all ACK/dispatch paths are absent.
Recording that no event was scheduled must never manufacture a PREPARE or effect receipt.

### Apply once, then witness independently

Treatment replaces each chosen wheat state with air through a reviewed no-drop native operation.
It must not call a drop-producing destroy operation, `Block.getDrops` for its own output, inventory
transfer, replanting, or reward settlement. Immediately recheck each next target against the captured
precondition before its mutation. Record attempted order, return values, and exceptions as adapter
diagnostics, then independently observe **all** candidates, supports, guard blocks, item entities,
containers and any custody state. A native return value is not sufficient evidence of the post-state.

All-target preflight is not a multi-block transaction: synchronous neighbor callbacks or a failure
after one successful mutation can leave a prefix changed. Stop on the first mismatch/refusal/error;
never continue, compensate, restore, select substitutes, or retry automatically. If an independently
captured outcome proves a known partial failure, the on-time START may settle as scheduler FAILED
with no `effect_tick`; the native evidence separately retains actual attempt tick and partial changed
positions. **FAILED does not mean zero physical mutation.** If effects or witness durability are
uncertain, leave the PREPARE pending/held. Quarantine a possibly partial or unknown START and block
further adapter dispatch and scored harvesting until explicit review; END cannot repair that state.

| Condition | Scheduler/native treatment |
| --- | --- |
| Fully witnessed on-time treatment | APPLIED at the scheduled tick, with an evidence ID resolving to the complete independent observation; harvest acceptance remains separate. |
| Fully witnessed sham or zero-rounded START | APPLIED for the declared verified no-op at that tick; record zero physical mutations and do not count it as measured loss. |
| On-time preflight failure with known unchanged state | FAILED, with actual evidence and no effect tick; failed slot remains in the denominator. |
| Known partial mutation | FAILED can record the failed operation; independently retain partial effects and quarantine. |
| Unknown effect, torn evidence, or uncertain ACK/write | Hold/quarantine; no blind acknowledgement or mutation retry. |
| Late START or END | MISSED; no retroactive mutation or restoration and no opportunistic rescheduling. |
| Exact duplicate receipt | Core idempotence applies; adapter dispatch must still refuse a second physical attempt. Conflicting/foreign receipts fail. |
| Settled on-time END | APPLIED for non-restorative lifecycle completion only; receipt time is not proof that crops recovered. |

After restart, existing pending PREPARE requires explicit reconciliation. APPLIED requires independent
evidence of the complete declared operation at its scheduled tick. NOT_APPLIED requires affirmative
external evidence of no application; absence of a receipt or air blocks alone cannot establish that.
Known partial failure may reconcile FAILED; unresolved world/save/journal order remains held. Exact
current block shape cannot establish historical causation or effect time. No automatic restorative
END, replay, crop replacement, inventory repair, or reward correction follows reconciliation.

## 6. Independent physical evidence and real harvest

A proposed dedicated read-only witness captures native block states, farmland properties, native
item entities (UUID, item ID, count and position), and container/cargo snapshots through a path separate
from adapter claims. An external fixture runner retains the raw server responses and a separately
versioned parser/verifier. The verifier must reject a consistent-looking adapter ledger when only
the native witness is altered or disagrees. A shared process does not make witnesses causally
independent, but neither may the observer reconstruct values from the adapter's expected counts.

Maintain three evidence classes: configured intent/digests; observed native state with actual ticks;
and later harvested material. The observer's snapshot hash identifies captured bytes, not an inherent
proof of authenticity. Bind each record to world, trial, dimension, source build, phase, actual tick,
monotonic capture sequence, and previous evidence identity. Preserve raw errors/truncation as failures.

The fixture's post-event harvest uses the native mature-crop break/drop path on each surviving crop,
with a fixed empty-tool/no-enchantment context. It removes real blocks and produces real native item
entities. It is **not** a prediction by summing `Block.getDrops`, nor a direct grant of expected wheat.
Do not reuse the adapter's destroyed-count field, the village harvest counter, or a scheduler receipt
as the harvest metric. A raw native entity query independently sums **wheat item counts**, not entity
counts, because stacks can merge. Record wheat seeds separately; no exact seed-count equality is
assumed. Unexpected loot types or changed loot resources invalidate the fixture instead of being
normalized away.

Use an enclosed, bounded collection volume with no preexisting items, players, mobs, collectors,
inventory producers, or item pickup/despawn during the measurement interval. Capture zero wheat and
seed items immediately before injection, zero injection-produced items after START and END, zero
items immediately before the later harvest, and actual resulting item counts immediately after the
harvest and at the next native tick. Retain an enclosing guard-volume query to detect escaped items;
missing/unreadable/outside output invalidates conservation. Containers and actor cargo must remain
unchanged. A later collection transfer, if added, requires its own native source/output reconciliation
and is not allowed to manufacture or hide missing harvest items.

## 7. Predeclared six-world correctness cohort

Propose two seed values, **23001 and 23002**, each used for both the explicitly recorded scenario-seed
and world-generation-seed fields. For each seed create three genuinely fresh world directories with
distinct persistent world UUIDs: treatment, sham, and no-event. Do not clone a prior save, reuse a
failed world as a replacement, or infer freshness from a different trial label. This gives six planned
slots; repeated captures or eight plots are not additional independent worlds.

The shared scenario configuration has one scope and one `crop_failure` rule, count 1, all eight
explicit candidates, onset exactly 1200, duration exactly 40, and intended severity exactly 500000
ppm. The native fixture has wheat at age 7 at `(x,64,z)` for x in 0..3 and z in 0..1, each over farmland
at y=63. A proposed permitted box from `(-2,62,-2)` through `(5,67,3)` contains the fixture; its exact
support, lighting, hydration, enclosure and guard template must be frozen and hashed before any run.
No other wheat is eligible. This admits eight candidates and k=4; shared pairing/ranking applies
even though mode/trial identities differ. Independent rank oracles must be frozen before adapter tests.

Freeze the actual Forge/Minecraft/mod JARs, datapacks/loot resources, fixture/harness/verifier hashes,
all environment settings, run order, seeds, trial IDs, clock contract, and expected bindings before
the cohort. Use randomTickSpeed=0, verified growth inactivity, no village controller/citizens, and
no external block modifiers. Do not use the historical baseline's accelerated crop-tick setup. The
absence of agents is intentional for physical correctness; it cannot substantiate adaptive recovery.

| Absolute native game tick | Fixed operation and validity condition |
| --- | --- |
| At or before 1000 | Finish fixture setup, independently establish eight mature crops/supports and zero output, register bindings, and arm the run. This gives at least 200 ticks of lead time. |
| 1199 | Independent before-window observation of the same full fixture and output/custody state. |
| 1200 | START or matched observer boundary. Capture authoritative preflight and immediate after state at the tested server-thread hook; treatment destroys exactly four without drops. |
| 1201 | Independent post-START observation; expected standing mature wheat is 4/8/8. |
| 1240 | END or matched observer boundary; verify there was no restoration or material transfer. |
| 1241 | Independent post-END observation, still 4/8/8 and zero injection-produced items. |
| 1260 | Verify the unchanged pre-harvest state; physically harvest each surviving mature wheat through the native drop path and capture actual resulting item entities. |
| 1261 | Independent final block/item/container/custody capture before any pickup. Record actual harvested wheat, seeds, empty harvested positions and unchanged supports. |

Ticks are `getGameTime()` values, not an offset from when setup happens to finish. If setup is late,
the trial is invalid and retained. If the scheduled hook is missed, retain the MISSED condition.
Never move onset to “now plus lead time,” reset game time, change duration, repeat a failed injection,
or extend the scoring window to obtain the expected counts. A setup-invalid trial is not fabricated
as a successful no-event control. Observation/harvest deadlines are validity gates too.

| Seed | Mode | Before mature wheat | Destroyed at START | Real harvested wheat expected |
| --- | --- | ---: | ---: | ---: |
| 23001 | Treatment | 8 | 4 | 4 |
| 23001 | Sham | 8 | 0 | 8 |
| 23001 | No-event | 8 | 0 | 8 |
| 23002 | Treatment | 8 | 4 | 4 |
| 23002 | Sham | 8 | 0 | 8 |
| 23002 | No-event | 8 | 0 | 8 |

These are **prospective expectations, not measured results**. For each seed, acceptance requires
independently measured sham-minus-treatment and no-event-minus-treatment wheat losses of four,
and sham-minus-no-event difference zero. Before harvest, sham and no-event must preserve all eight
crops and relevant physical state; naturally removing them in the later measurement harvest is
not an injection-induced control change. All arms use identical observation and harvest machinery.
If native mature-wheat loot does not produce the pinned one-wheat-per-crop behavior, report the
changed physical premise and fail the fixture rather than hardcoding output into the world.

This is a small deterministic correctness cohort. It supports no claim of treatment effectiveness
across natural colonies, statistical learning advantage, causal communication benefit, recovery,
occupation persistence, or job specialization.

## 8. Named tests and evidence requirements — all proposed, not run

| Test | Required adverse/positive condition and oracle |
| --- | --- |
| CF-01 SIX-WORLD-HARVEST | All six predeclared fresh slots; before=8, no-drop injection, physical post-event harvest, independently counted wheat 4/8/8 for each seed; complete raw evidence and control preservation. |
| CF-02 PAIRED-SUBSET | Fixed independent ranking oracles; candidate input reordering invariance, same pair across modes/trials/worlds, exact tie-break, repeated seed reproduction. No mode-specific event ID in ranking. |
| CF-03 SEVERITY-BOUNDARY | N=8 boundary counts specified above; N=1/32 and ppm 0/1000000; negative/overflow/out-of-domain inputs rejected; positive zero-rounded case explicitly reports no loss. |
| CF-04 MODE-CONTRACT | Reject manifest/event/mode/ppm disagreement; sham performs no mutation; no-event emits no transition but receives equal independent measurement and binding checks. |
| CF-05 FOREIGN-BINDING | Foreign real world, dimension, trial, run, schedule, event, phase, pair, scope/targets or evidence rejected without journal/world changes. Raw generic-scheduler opens cannot bypass adapter admission. |
| CF-06 NATIVE-CONTEXT-DRIFT | Change only adapter, precondition, rank/rounding, clock, fixture, measurement or loot bytes; inconsistent sidecar/independent marker/cohort digest blocks open, including empty controls. Retain original bytes and failed opens. |
| CF-07 PARTIAL-CREATION | Terminate at each proposed registration/sidecar/journal/READY boundary; missing or conflicting components fail closed with no world mutation or silent recreation. Actual durability guarantee is a design-review prerequisite. |
| CF-08 NATIVE-BOUNDS-LOADING | Signed32 coordinates accepted by scenario but outside actual native bounds, missing dimension, unloaded crop/support/guard chunk, wrong region and packed-coordinate loss all fail before mutation; assert no force-load/generation. |
| CF-09 ALL-TARGET-PREFLIGHT | One late-listed candidate wrong/immature/missing, changed farmland or unexpected block entity prevents every mutation; no filtering, substitute target, or denominator shrink. |
| CF-10 OVERLAP-OWNERSHIP | Extra choices, overlapping contexts, and active native crop leases are rejected; no lock stealing, citizen cancellation, deferred tick execution or overlapping mutation. |
| CF-11 MISSED-TIMING | Setup after 1000, skipped START/END, backward clock, wrong hook phase or duplicate hook invocation; never shift ticks, apply late or restore at END. Retain invalid/missed evidence separately. |
| CF-12 DUPLICATE-DISPATCH | Repeated call before ACK, repeated receipt after ACK, and conflicting receipt; at most one physical attempt for the same bound START and no second harvest-loss credit. |
| CF-13 MID-APPLY-FAILURE | Refuse/throw after 0, 1 and 3 of four changes; synchronous neighbor drift before the next change; independent after map retains exact prefix effects. Stop, quarantine, no rollback/retry; FAILED may contain partial effects. |
| CF-14 RESTART-HOLD | Interrupt before effect, after a prefix, after full effect before witness/ACK, and after ACK before world save; unknown histories stay held. Positive reconciliation needs independent historical/tick evidence, never block shape or receipt absence alone. |
| CF-15 NON-RESTORATIVE-END | Successful, failed, missed and restarted START histories; END never recreates wheat, returns seeds, edits inventory/cargo or grants credit. Quarantine cannot be cleared by END. |
| CF-16 NATIVE-WITNESS-NEGATIVE | Keep adapter/journal internally consistent while changing only native block, item-count, tick, UUID, support, raw response or container evidence; independent verifier must reject each mismatch. |
| CF-17 DROP-CONSERVATION | Injection produces no wheat/seeds/items in any arm. Real harvest uses native drops; merged stacks, missing/escaped output, unexpected items, preexisting output and extra producers cannot falsely pass actual yield. |
| CF-18 CUSTODY-COMPATIBILITY | Existing FARM_SEED/FARM_CROP/HARVESTING/return-seed/held cases retain native seed and cargo ownership. Adapter rejects owned targets and never invokes settle/learn, clears a lease, rewrites cargo, or masks an existing uncertain work phase. |
| CF-19 SOURCE-OBSERVATIONS | Separate actor fixture: before START, changed private future plans do not alter actor-accessible facts; after a real change, only an actual loaded/in-range native sense may change mature facts. Stale and out-of-range facts retain existing semantics. |
| CF-20 DATA-ISOLATION | Canary private seed, mode, future tick, target/rank, severity, manifest and diagnostic IDs cannot reach actor observations, messages, policy features, reward/outcome rows or learner state through the adapter. Hold observed world state fixed and vary only the private plan to test data dependence. Normally sensed coordinates may equal a planned target without constituting a leak; subsequent independently sensed physical changes remain allowed. |
| CF-21 EVIDENCE-IO-CAPACITY | Observer unavailable/truncated, capacity exhausted, or journal/sidecar/witness flush failure before/after effect; no unsupported APPLIED, no guessed success, no automatic recovery, complete retained failure state. |
| CF-22 DENOMINATORS | Missing, invalid-setup, failed, missed, partial, unresolved, harvest-failed and completed slots all appear. Attempt IDs prevent a successful repeat from replacing its earlier failure. No per-plot pseudoreplication. |

Pure contract tests address ranking/admission/binding and verifier negatives. Fault tests address
creation, dispatch, evidence and restart boundaries. Exact-head Java 17/Python contracts and Forge
compilation precede native runs; native fixtures and existing custody/production/restart regressions
precede runtime promotion. Adversarial native cases have their own predeclared slots and denominators,
separate from the six nominal slots; a small nominal cohort is not a substitute for those cases.
No C14-02 test in this table has run yet.

## 9. Retained artifacts, gates, and unresolved review decisions

Retain the original six-slot registration, every attempted world and failure reason, source/tree/JAR
hashes, generated scenario manifests, native context bytes and independent binding records, native
world UUID/seed/dimension queries, environment and fixture readbacks, scheduler journals after owners
close, adapter attempts, independent raw snapshots, native harvest responses, per-world verifier
outputs, and one cohort table that includes every planned slot. Keep raw stage logs and artifact
digests even when a runner fails before effect or harvest. Separate denominators for planned worlds,
setup-valid worlds, on-time intents, complete/partial/unknown effects, successful real harvests and
fully valid comparisons. Do not pool citizens or plots as independent worlds.

| Phase | Current C14-02 state and next gate |
| --- | --- |
| Requirements | Original wording preserved; destruction slice and physical/control oracles proposed for review. |
| Design | Proposed only; native identity publication, tick ordering and independent witness contracts require review. |
| Test design | Named cases and six nominal slots proposed; fixed subset oracles and exact fixture resources still to be frozen. |
| Implementation | Not run; no adapter, native registration, witness, harness or actor integration added. |
| CI and QA execution | Not run for C14-02; previous scheduler/scenario results are prerequisite evidence only. |
| Native physical validation | Not run; no measured 4/8/8 yields or verified sham claimed. |
| AI/learning validation | Not run; no model, policy, reward or recovery change proposed here. C03 dependency retained. |
| Integration/release | Not run; baseline and stacked PRs remain separate decisions. |
| Acceptance | Open; actual harvest-loss/control evidence and all applicable dependency gates remain outstanding. |

Concrete decisions to resolve before code: the durable independent native-context binding and its
partial creation/rollback behavior; the exact server hook and tick/capture ordering; the native no-drop
operation and synchronous callback behavior; independent read-only witness coverage/encoding and
durability; the frozen item-collection/guard geometry and loot resources; and conflict checks against
the existing farm custody/lease state. These are implementation risks with named tests, not reasons
to weaken actual harvest measurement or accept adapter testimony as proof.

## 10. Relevant reference applications and limits

This section applies the **already recorded primary-source review** in the pinned C14 reference
record. No new paper reading, new Drive inspection, or independent MARBLE replication is claimed.
The configured refs/ collection remains relevant where it supplies these mechanisms; unrelated
politics, topology or game-theory details do not enter this crop adapter merely to increase citations.

| Previously read source and exact location | Application here | Tests/evidence motivated | Transfer limit |
| --- | --- | --- | --- |
| Pham, *Software Agents for Internet-Based Systems and Their Design*, in Jain et al. (2002), ch. 5 §4; printed pp. 113–117 / physical PDF pp. 131–135; [book DOI](https://doi.org/10.1007/978-3-7908-1786-7). | Separate a due transition from delivered/settled execution and from physical effect; preserve pending/expired states. | CF-11–CF-15 and separate intent/effect denominators. | Communication infrastructure does not establish atomic multi-block mutation, world-save durability, or this journal protocol. |
| Chan et al., *Visibility into AI Agents*, v6, §3.1 physical p. 5 and §§3.3–3.3.2 physical pp. 7–8; [primary version](https://arxiv.org/abs/2401.13138v6). | Stable identities, activity provenance, separate access scope, and explicit retained failures; private diagnostics are not actor facts. | CF-05–CF-07, CF-16, CF-20–CF-22; native-context and witness bindings. | Inspectable logs and identifiers neither authenticate actual crop loss nor solve cross-file/world atomicity. |
| Project Sid v1, §§2.3 and 3.2; §8.2 only for the specialization-measurement boundary; [primary version](https://arxiv.org/html/2411.00114v1). | Compare intended effects with independently observed results; keep later occupational evidence separate. | CF-01, CF-16–CF-20; real output counts and unchanged control state. | Does not authorize LLM controllers, off-thread mutation, scripted recovery, or a specialization claim from this fixture. |
| Zhu et al., *MultiAgentBench*, §§3.2–3.3, especially printed p. 8584 / physical PDF p. 5; [ACL publication](https://aclanthology.org/2025.acl-long.421/). | Distinguish scheduler activity, physical injection, harvest outcome and subsequent adaptation; preserve complete denominators. | CF-01 and CF-22; separate nominal/adverse cohorts and per-world comparisons. | Authored benchmark roles are not emergent occupations; MARBLE is the associated implementation, not independent replication; six worlds do not establish a learning benefit. |

The user's PA4 dossier remains a secondary analysis aid: P06, physical pp. 30–33, and P42, physical
pp. 185–188, as recorded in the same source memo. Its failure/verification and evaluation distinctions
support retaining preflight rejection, known partial effect, unknown effect, missed timing and later
harvest failure as separate observations. Those labels do not determine causation by themselves.
The SHA ranking, caps, ppm flooring, clock values, fixture geometry and binding proposal above are
project engineering choices whose validity must come from review and the specified tests.
