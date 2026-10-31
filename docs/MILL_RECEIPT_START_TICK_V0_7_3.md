# v0.7.3 — Observed mill start tick

## Purpose
This branch extends the existing `feat/first-mill-create-v3-2` real-Create mixin implementation. It records a separate, server-observed powered processing start time, rather than fabricating a start time from the completion tick.

## Behavior
- `MillExperimentTrace.sampleCycle` records `processingObservedTick` when server-side Create millstone state has input wheat, positive timer, and nonzero rotational speed.
- `MillExperimentTrace.verifiedProcessingStartTick` accepts only observations tied to the same citizen's job and machine, not earlier than authorized delivery, and strictly before the real `process()` completion callback.
- `MillProcessReceipts.record` now fails closed and taints the job when the observation is missing.
- The `SavedData` receipt serializes `startTick`; older receipts load with sentinel -1 and do **not** satisfy the new verified-receipt gate.

## Deliberate limitations
- This patch does **not** integrate the v0.7.2 `VerifiedMillReceiptBridge`, persistent inbox or reward ledger.
- The observed tick is sampled from a live machine during a server tick, not necessarily the exact internal Create process timer start. The field means *first observed active processing*, not mathematical process start.
- An experiment completed before a sample tick is intentionally rejected.
- Existing client/server Forge compilation and game tests have **not** been executed in this session.

## Required end-to-end tests
1. Confirm Minecraft/Forge/Create dependencies compile on Java 17.
2. Start real server/client, power one real millstone, authorize a citizen-delivered wheat unit and confirm `startTick < tick` in persisted receipt.
3. Simulate early processing before a sampling tick; confirm NO_RESEARCH_CREDIT.
4. Confirm mixed input, foreign output, duplicate jobs, and unauthorized transfers cannot produce verified receipts.
5. Save, restart, inspect receipt; ensure old-version receipts remain ineligible until a new live experiment occurs.
6. Verify no rewards are credited until the durable ledger and social-memory integration have actually been wired.
