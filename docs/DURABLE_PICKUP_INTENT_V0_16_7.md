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
7. NOT IMPLEMENTED: complete scans of *unloaded* citizen NBT, cross-file
   backup rollback/high-water mark anchoring, an authorized reconciliation
   workflow, or independent inventory proof.
8. NOT VERIFIED: forced-kill real Forge acceptance for interruption boundaries
   with independent source, actor cargo and destination inventories.

## Scope and caveats

The motor hook, loaded-citizen restrictive restart classification, eager
journal validation, ownership marker and normal server-stop cleanup are wired.
Full unloaded-citizen reconciliation, external rollback anchors, physical
recovery controls and real crash verification are not. The new admin audit
is observational only. A legacy world with an existing
journal but no marker deliberately fails closed; migration must be explicit. Existing v0.16.6 session fencing remains the
primary protection for restored report-policy tasks.
The class does not provide atomic inventory transactions, signed anti-rollback
checkpoints or an external anchoring mechanism. A whole-file rollback or valid
prefix truncation cannot be detected without a separately anchored high-water mark.
Do not enable recovery, autonomous retries, rewards, Create tech unlocks or ML
weight updates on the basis of this component. No LLMs.
