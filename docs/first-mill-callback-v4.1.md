# First Mill v4.1 — direct Create process callback (experimental)

## Prior passing baseline
Commit `2a4d838e` passed: Create server integration, powered milling, Sable hauling and milling, and evidence survival after graceful server restart.

## Direct callback implementation
A required Mixin targets `MillstoneBlockEntity.process()` using HEAD and TAIL injections. It snapshots the mill's input wheat quantity and output flour quantity immediately before and after the **actual Create processing operation**, and accepts only transitions consuming exactly one wheat and increasing flour output.

`MillProcessReceipts` records one candidate receipt per haul job UUID in per-dimension `SavedData`. The callback matches a recent delivered experiment in nearby villagers; it requires exactly one candidate. Receipts are deduplicated and inspectable through `/sable mill-process <job-uuid>`.

The Sable First Mill dedicated-server test demands a `MILL_PROCESS VERIFIED_CALLBACK` receipt containing `wheatBefore=1 wheatAfter=0`, while ensuring `NO_RESEARCH_CREDIT`.

## Critical limitations
- Mixin instrumentation is **unverified until CI passes**. The Mixin must be loaded in both the Forge dev launch and packaged jar.
- A single recent villager match does **not** prove exclusive access to a shared millstone. External agents could put wheat into the same machine; attribution is deliberately conservative but not yet secure. Receipt is a direct Create callback and linked candidate, not verified exclusive source provenance.
- The world receipt is persistent only after successful Minecraft world save. Create inventory mutation and receipt storage are not a cross-save atomic transaction.
- No recipe unlocks, reward, colony knowledge sharing or learning policy changes are enabled.
- Strong next step: reserve individual machines for individual jobs and prove exclusive control during the recipe window, with cancellation and crash recovery; test adversarial extra input and restart replay before any learning credit.
