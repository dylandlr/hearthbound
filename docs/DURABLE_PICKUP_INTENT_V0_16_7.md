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
