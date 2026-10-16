# First Mill v5.1 — fail-closed callback attribution

## Confirmed baseline
Commit `2ada669f` passed all four dedicated-server CI workflows. The v5.0 post-delivery extra-input test was introduced later, and its first gameplay run exposed an **outdated negative-control assertion**: the system correctly returned `MILL_PROCESS INVALIDATED` for a tainted job, but the test erroneously required `MILL_PROCESS NONE`. The test now explicitly accepts only `INVALIDATED` and `NO_RESEARCH_CREDIT` for tainted experimental evidence.

## New enforcement
When the actual Create `MillstoneBlockEntity.process()` callback detects an invalid wheat/flour transition, the reserved experiment is permanently marked tainted. The callback now also invalidates the held reservation if **zero or multiple matching authorized citizen delivery traces** exist, or if the matched citizen conflicts with the reserved job. A second process invocation for an already-receipted one-wheat job invalidates the same reservation.

The per-dimension `MillReservations` taint markers survive a saved-world restart. `MillProcessReceipts.hasReceipt` rejects tainted jobs and the admin `/sable mill-process <uuid>` query reports `MILL_PROCESS INVALIDATED`.

## Acceptance and remaining limitations
The dedicated-server gameplay script attempts a post-delivery extra-wheat injection into a separately powered mill and requires direct callback invalidation. Other regressions verify the original Sable production pipeline, reserved-job uniqueness, clean admission, and journal/receipt restart.

A replacement by the **same** wheat item kind and count remains indistinguishable using an inventory count plus timestamp alone; this is not an item-instance tracking or tamperproof inventory system. A complete provenance guarantee needs physically enforced access at all insertion paths and transaction ownership. No recipe unlocks, XP, teaching rewards or Outcome Ledger allocations are enabled. Treat the newest gameplay CI as pending until confirmed green.
