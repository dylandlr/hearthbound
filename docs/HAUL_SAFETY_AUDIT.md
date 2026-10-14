# Hauling safety audit (development)

## Current fix
Before extraction, the source job checks whether the destination chunk is loaded and the output inventory can accept at least one wheat. For Forge item-handler inventories, the check uses simulated insertion. For plain containers it checks slots and stack limits.

## What this does NOT guarantee
- Destination inventory may change after preflight, so output can still become blocked.
- Source and destination saves and villager NBT saves are **not atomic**. Crash-recovery conservation is not solved.
- No per-inventory reservation, actor concurrency protocol, transaction journal or idempotency key.
- Server restarts and chunk unloads have not been tested.
- The independent Forge compilation workflow must be green before interpreting this as a working Minecraft mod.

## Required next architecture
Introduce a world-level job ledger with a unique job ID, a reservation stage and an explicit transfer log, ideally with controlled rollback/reconciliation and immutable before/after item counts. Test crash injection between extraction, journal save, delivery and world save; target conservation of wheat across repeated restart trials. Only then enable multi-agent cargo hauling by default.

## Regression scenarios
1. Destination full at dispatch: source count does not change.
2. Destination unloaded: task waits without loading distant chunks or removing cargo.
3. Destination fills after preflight: retain cargo; stop until player repairs output.
4. Source empty: pause, no cargo.
5. Restart at source, mid-haul and after delivery: count items before and after.
6. Two citizens competing for one source slot: verify no unowned inventory modifications (not yet supported).
