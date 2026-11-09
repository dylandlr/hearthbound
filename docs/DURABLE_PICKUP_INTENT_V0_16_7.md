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
