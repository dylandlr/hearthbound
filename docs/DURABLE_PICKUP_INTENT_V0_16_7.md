# v0.16.7: durable pickup extraction intent/outcome slice

This draft builds on v0.16.6 (#192) and targets Track A of #191.
It adds a **standalone Java 17 transaction journal** and a fail-closed experimental hook around real report-policy Minecraft extraction.

Each job has one world-bound, fsync-forced intent followed by at most one
fsync-forced outcome: `EXTRACTION_EMPTY` or `CARGO_RETURNED`.
An intent with no outcome is `UNRESOLVED` on replay and requires quarantine.
In particular, absence of a completion record is **not proof of failed extraction,
an empty chest, or safely transferable cargo**. A CARGO_RETURNED outcome describes
the extraction call only; it is not evidence that the destination received wheat.

## Integration status (live restart/fault acceptance NOT yet passed)

1. Implemented: only report-policy jobs invoke the bridge. The motor checks
   assignment/world/executor/job IDs and forces intent BEFORE `extractWheat`.
   Failure denies extraction. No-transaction jobs retain legacy semantics.
2. Implemented: the physical motor's returned empty/cargo result is forced to
   the journal. An extraction exception leaves an unresolved intent; a failed
   outcome force quarantines the job. Cargo is written to in-memory citizen NBT
   before the outcome force, but this is NOT save-atomicity.
3. Implemented: the server-stop callback closes the writer. Journal open validates
   world, framing, sequence and hash chain; duplicate job intents fail closed.
4. Partially implemented: when a saved report-policy job is encountered in a
   loaded citizen after restart, its world/executor/job identity is compared to
   the journal. Missing intent or recorded empty outcome pauses; unresolved,
   cargo-returned, identity mismatch and journal failure quarantine. This is
   restrictive classification only, NOT resumption or exact recovery.
5. Implemented: eager server-start journal open and a world UUID-bound,
   fsynced ownership marker. A missing marker/journal pair, orphan file,
   corrupt journal or foreign identity blocks future report-policy extraction.
   New-world initialization is marker-reservation-first. Startup blocks on
   invalid files; it does NOT repair or migrate them.
6. Implemented: permission-2 `/hearthbound-pickup-journal` provides a
   read-only journal-wide summary and bounded unresolved job/actor/tick IDs,
   including transactions for unloaded citizens. It does not load chunks,
   scan their NBT, or reconcile actual inventory.
7. Implemented: `/hearthbound-pickup-citizen-audit` joins the full journal to
   currently loaded marked villager NBT across dimensions, showing `not_loaded`,
   `mismatched`, and `hold_for_review` counts. Citizens outside the loaded set
   remain UNKNOWN; no chunk/entity-region loading, inventory scans, or retries.
   The administrative `resume` method now rejects paused report-policy jobs,
   closing a path around the restarted-job gate.
8. NOT IMPLEMENTED: complete scans of *unloaded* citizen NBT, cross-file
   backup rollback/high-water mark anchoring, an authorized reconciliation
   workflow, or independent inventory proof.
9. NOT VERIFIED: forced-kill real Forge acceptance for interruption boundaries
   with independent source, actor cargo and destination inventories.

## Scope and caveats

The motor hook, loaded-citizen restrictive restart classification, eager
journal validation, ownership marker and normal server-stop cleanup are wired.
Full unloaded-citizen reconciliation, external rollback anchors, physical
recovery controls and real crash verification are not. Loaded-villager audits
are read-only comparisons and may not substitute for independent evidence. The new admin audit
is observational only. A legacy world with an existing
journal but no marker deliberately fails closed; migration must be explicit. Existing v0.16.6 session fencing remains the
primary protection for restored report-policy tasks.
The class does not provide atomic inventory transactions, signed anti-rollback
checkpoints or an external anchoring mechanism. A whole-file rollback or valid
prefix truncation cannot be detected without a separately anchored high-water mark.
Do not enable recovery, autonomous retries, rewards, Create tech unlocks or ML
weight updates on the basis of this component. No LLMs.

## v0.16.7 process-termination storage acceptance

`PickupJournalForcedKillTest` launches a separate Java 17 JVM and forcibly
terminates it **without normal shutdown or closing the journal** after:

- **BEFORE_INTENT:** no fabricated transaction may appear.
- **AFTER_INTENT:** the intent must replay as UNRESOLVED; quarantine required.
- **AFTER_EMPTY_OUTCOME:** the persisted empty-extraction receipt must replay.
- **AFTER_CARGO_OUTCOME:** cargo-returned outcome must replay, without implying delivery.

The child prints its readiness sentinel only after the relevant `FileChannel.force(true)`
returns. Parent kills the process and reopens the exact journal from disk.
Tests execute through `scripts/test-research-journals.sh`; results must be
obtained from GitHub Actions at the exact head before claiming passage.

**This is storage-only acceptance.** It does not terminate the real Forge JVM
during a Minecraft block-entity operation, verify world saves, reconcile
inventory, or prove power-loss durability on all filesystems. Those are
separate physical acceptance gates. A delayed, missed, or errored test never
authorizes replay or new rewards.

## Physical Forge evidence-to-journal linkage (new acceptance assertions)

The existing real Forge scripts now verify that the independent, read-only
`/hearthbound-pickup-journal` shows one `EXTRACTION_EMPTY` outcome for the
actual failed A pickup before any scout recovery. After B is actually hauled,
the journal must show two total jobs: one empty extraction, one cargo-returned
extraction, and zero unresolved intents. This is checked alongside physical
source A=0, source B=0, destination=1 inventories.

Both clean-restart and deliberately killed-server acceptance scripts require
the original durable A extraction receipt to survive boot. In the crash case,
unsaved villager NBT is deliberately lost while the journal's A receipt survives:
the journal does **not** fabricate or restore the citizen's missing private
negative memory. World-swapped copies must return FAIL_CLOSED because the
world UUID binding differs. The clean recovery arm additionally requires the
later B cargo-returned receipt with independently observed inventory deltas.

These tests use real Forge/RCON and are **new assertions, not completed passes**.
Their reliability, including the new journal-integrity startup path, must be
judged at the exact GitHub Actions commit. A green storage-only kill test
cannot substitute for a live server crash with physical inventory inspection.

Next: add deterministic real-server crash hooks around each motor boundary,
in disposable worlds only; measure whether world inventory saves can diverge
from forced journal state, then design explicit operator-controlled
reconciliation for every divergence without inferring delivered cargo.

## Manual cancellation guard

`SableHauling.cancelBeforePickup` now consults the durable pickup journal for
report-policy jobs even if saved citizen NBT contains **no cargo**. Only a job
with no committed extraction intent or a matched `EXTRACTION_EMPTY` outcome
may use the existing no-cargo cancellation path. `UNRESOLVED`,
`CARGO_RETURNED`, foreign identity and unavailable journals all deny
cancellation. This prevents an operator from releasing the source claim based
only on a stale NBT snapshot after an extraction crash. The pure-Java
`PickupRecoveryGateTest` covers each decision state.

This is a restriction, not proof that an actual inventory is empty and not an
automatic recovery mechanism. The real Forge forced-crash scenarios and
independent item delta checks remain necessary.

## Dedicated real Forge kill-at-motor-boundary CI

The opt-in `PickupCrashBoundaryProbe` is **disabled by default**, not exposed
as a player/admin command, and accepts only a disposable world named
`pickup-crash-boundary-world` with both explicitly supplied test JVM
properties. The actual report-policy motor emits and fsyncs a test-only
marker immediately after one of three physical execution boundaries:

- `AFTER_INTENT`: forced intent persisted; no inventory extraction yet.
- `AFTER_EXTRACTION`: the real `extractWheat` returned; cargo NBT/outcome
  persistence has not yet happened.
- `AFTER_OUTCOME`: real extraction, cargo NBT update and durable outcome
  persist completed; block-entity and citizen NBT saves are still not atomic.

The dedicated `real-pickup-crash-boundaries.yml` workflow creates a fresh
disposable, loopback-only world, saves source and scout baseline evidence,
disables game saving, dispatches one actual policy haul, waits for the
forced test-only marker, positively identifies the RCON-owning Java process,
and kills that exact JVM with SIGKILL. It then restarts the same saved world
without the probe enabled.

Expected journal replay for the first two boundaries is `UNRESOLVED`, and
for `AFTER_OUTCOME` it is `CARGO_RETURNED`. Independently saved source,
alternate source, and destination chest inventories must remain at
pre-dispatch baseline 3/1/0; unsaved assignment NBT must not reappear.
If a killed server actually saved different data, the test must fail and
the discrepancy must be investigated, **not waived**. No replay, credit,
reward, automatic retry, or fabricated cargo is allowed.

This is an acceptance *harness*, not a passed test. An external CI process
performs termination: the mod itself never issues SIGKILL or calls
`Runtime.halt`. If the kill does not arrive, the probe times out and
fails the motor rather than proceeding. The three cases are separated
into independent test worlds. No real-world power-failure or fully
crash-atomic Minecraft inventory guarantee is claimed.

## Job-bound forensic verification

The permission-2 `/hearthbound-pickup-job <uuid>` command now returns
the exact persisted intent's job, world, executor, source, assigned and
attempted ticks, and state. It is read-only, does not access player
inventory, load chunks, or authorize any action. Unknown UUIDs report
`status=ABSENT`; unavailable/corrupt journals report `FAIL_CLOSED`.

The real Forge crash-boundary verifier requires the job UUID from the
original physical dispatch, the state expected at that exact kill boundary,
the source position, and the world UUID in the forced boundary marker to
match this one persisted record. Journal aggregate counts remain useful
for secondary checks, but cannot independently prove job-level provenance.

These assertions are committed, not yet certified by real Minecraft CI.

## Source-level quarantine across distinct job IDs

`PickupSourceAdmission` now consults the journal before committing a new
report-policy pickup intent. The check happens under the Forge bridge's
synchronized transaction boundary, so another pending extraction cannot
race between admission and `begin`.

A fresh job UUID **cannot bypass** an older `UNRESOLVED` intent or
`CARGO_RETURNED` extraction for the *same world and source*. Both states
deny another extraction. `EXTRACTION_EMPTY` does not block an independently
validated future assignment, though it never proves the chest is currently
empty. Other sources can continue; source-policy denials are not journal-I/O
failures and do not poison the entire server's writer.

This is deliberately conservative: `CARGO_RETURNED` records extraction,
**not completed delivery**. A legitimate completed haul therefore also
blocks repeat report-policy pickups from the same source in v0.16.7 until a
future durable delivery/reconciliation protocol is accepted. Do not silently
clear this block based only on a citizen's COMPLETED phase, a chest count
snapshot, or an operator's assumption. No automated inventory mutation,
model update, research credit or technology reward is enabled.

`PickupSourceAdmissionTest` covers unresolved, cargo-returned, empty,
distinct-source, foreign-world, malformed and reused-job scenarios.

## v0.16.7: durable *insertion attempt* records (not delivered-item proof)

A source pickup and a destination insertion are now separately recorded in
the **same** world-bound, fsynced, CRC/hash-chained journal. For report-policy
hauls only, the motor forces an insertion intent before the actual Minecraft
destination `insert` operation. It records `INSERTION_RETURNED` only when
the insertion motor returned no remaining cargo, before citizen NBT is
marked COMPLETE. A partial insertion, thrown exception, or interrupted journal
force leaves `INSERTION_UNRESOLVED` and requires review.

- `NOT_STARTED`: no delivery intent recorded for this pickup.
- `INSERTION_UNRESOLVED`: insertion was attempted or possibly interrupted;
  physical cargo/destination inventory cannot be inferred.
- `INSERTION_RETURNED`: the real motor call returned no remainder and its
  outcome was fsynced. This **does not independently prove** that Minecraft
  persisted the destination inventory.

The original extraction state remains unchanged and `CARGO_RETURNED`
continues to **block new report-policy pickups from the same source** even
after `INSERTION_RETURNED`. That block may only be reconsidered after a
separately designed delivery verification protocol with independent physical
witness and crash-safe world-state checks. No automated recovery, science
reward, Create unlock or online ML update is authorized.

`DeliveryBoundaryContractTest` and `DeliveryJournalReplayTest` are
now part of the standalone Java 17 suite. The real Forge A-failure/B-delivery
acceptance script also demands `delivery_state=INSERTION_RETURNED` for the
actual B job. These are **new, unverified** latest-head assertions.

## Six-boundary real Minecraft crash matrix: insertion coverage

The disposable CI world now tests the original three extraction boundaries
**and** three destination boundaries. The physical `SableHauling` motor
emits an external-kill marker at these exact points, with no gameplay command
or in-mod process termination:

| Marker | Persisted pickup outcome | Persisted insertion state |
| --- | --- | --- |
| AFTER_INTENT | UNRESOLVED | NOT_STARTED |
| AFTER_EXTRACTION | UNRESOLVED | NOT_STARTED |
| AFTER_OUTCOME | CARGO_RETURNED | NOT_STARTED |
| AFTER_DELIVERY_INTENT | CARGO_RETURNED | INSERTION_UNRESOLVED |
| AFTER_INSERTION | CARGO_RETURNED | INSERTION_UNRESOLVED |
| AFTER_DELIVERY_RETURN | CARGO_RETURNED | INSERTION_RETURNED |

The external test kills the actual RCON-owning Java process only after the
specified marker has been forced to disk, then restarts a known baseline.
The verifier requires the **exact job UUID**, world UUID and source to match
the recovered journal and separately reads saved Minecraft chest inventories
(A=3, B=1, destination=0). These expected post-kill chest values depend on
having successfully disabled saving after the independent pre-dispatch
baseline; any unexpected save or inventory mismatch is a failure to
investigate, not a reason to modify the expected data.

The two delivery-intent/interrupted-insertion cases cannot tell whether
destination insertion physically happened. The returned-insertion case only
proves the motor result was recorded; it still does NOT prove the destination
inventory survived a server crash. No source is reopened, no item is
replayed, and no model/research reward is authorized on these records.

**Status:** harness authored and pushed, **latest-head CI not passed or
independently reviewed**. Success of these six cases is not an atomic
transaction guarantee across power failures, chunk saves or other plugins.

## Persisted insertion provenance in the exact-job audit

The read-only permission-2 `/hearthbound-pickup-job <uuid>` receipt now
includes `delivery_destination` and `delivery_tick` from the forced
insertion-intent frame in addition to `delivery_state`. Where no insertion
intent exists, those fields are `NONE` and `-1`, respectively.

`DeliveryJournalReplayTest` requires those exact fields to survive closing
and reopening the journal for both an interrupted insertion and a returned
insertion. The six-boundary Forge verifier checks that a destination/tick
appears only after the delivery-intent boundary and that the destination is
the real tested chest, `minecraft:overworld|10,101,2`.

These are provenance checks only. Even a matching destination and a durable
`INSERTION_RETURNED` frame do not establish a persisted inventory delta,
independent third-party witness, or safe automatic retry.

## Adversarial delivery-frame replay tests

`DeliveryJournalCorruptionTest` constructs real forced insertion-intent and
insertion-return records, closes the journal, then verifies fresh opens reject:

- Truncation into the final frame's header/payload (1 through 12 bytes);
- Same-length corruption of the final delivery frame;
- Valid delivery data attached to a different world UUID.

It also checks both intact controls: `INSERTION_UNRESOLVED` and
`INSERTION_RETURNED`. This test is included in
`scripts/test-research-journals.sh`, but latest-head CI execution is pending.

Important limit: a **valid-prefix rollback** removing an entire completed
frame is not detectable using this journal's internal CRC/hash chain alone.
External high-water anchoring and a separate physical-world witness remain
unimplemented. This new test does not claim to solve that limitation.
