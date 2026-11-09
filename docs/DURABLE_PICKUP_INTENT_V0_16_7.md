# v0.16.7: durable pickup extraction intent/outcome slice

This draft builds on v0.16.6 (#192) and targets Track A of #191.
It adds a **standalone Java 17 transaction journal**, not an enabled Minecraft motor integration.

Each job has one world-bound, fsync-forced intent followed by at most one
fsync-forced outcome: `EXTRACTION_EMPTY` or `CARGO_RETURNED`.
An intent with no outcome is `UNRESOLVED` on replay and requires quarantine.
In particular, absence of a completion record is **not proof of failed extraction,
an empty chest, or safely transferable cargo**. A CARGO_RETURNED outcome describes
the extraction call only; it is not evidence that the destination received wheat.

## Integration gate (NOT yet passed)

1. Resolve world ID and validate existing report-policy job/lease provenance.
2. Before the actual `extractWheat` call, write and force the unique intent.
   If this fails, pause/fail closed without touching inventory.
3. Call the existing physical extraction exactly once.
4. Persist/force the outcome before making new policy choices. If this fails,
   quarantine the job, and do not infer negative beliefs from NBT alone.
5. On startup, open and validate the journal BEFORE any citizen is eligible to
   act; match loaded/unloaded citizens against persisted intents and saved NBT.
   Missing journal/rollback, orphan NBT, unresolved intents and foreign world
   must block motor work until explicit reconciliation.
6. Add a forced-kill real Forge test at each interruption boundary with
   independent source, actor cargo and destination inventory observations.

## Scope and caveats

The standalone class is a storage primitive only; motor, save lifecycle,
journal ownership marker, operator controls, and live recovery are not wired.
Existing v0.16.6 session fencing remains the real-world fail-closed defense.
The class does not provide atomic inventory transactions, signed anti-rollback
checkpoints or an external anchoring mechanism. A whole-file rollback or valid
prefix truncation cannot be detected without a separately anchored high-water mark.
Do not enable recovery, autonomous retries, rewards, Create tech unlocks or ML
weight updates on the basis of this component. No LLMs.
