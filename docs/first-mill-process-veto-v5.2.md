# First Mill v5.2 — processing entry veto (experimental)

## Latest known fully verified baseline
Commit `2ada669f` completed all four Minecraft workflows. Later v5.0/v5.1 changes introduced the post-delivery attack test and explicit INVALIDATED result; recent CI must be checked before making claims about the new processing guard.

## Changes
Create `MillstoneBlockEntity.process()` now has a cancellable entry Mixin. On any **unreserved** millstone it permits normal Create operations. On a Hearthbound-reserved machine, `MillProcessReceipts.admitProcessing` requires exactly one wheat input, zero existing flour, precisely one matching authorized Sable insertion snapshot, and a matching non-tainted machine lease. A mismatch irreversibly taints the saved-world reservation and vetoes `process()` so the contaminated items remain for operator investigation. The existing TAIL callback remains responsible for recording a successful direct Create processing receipt.

The server-side end-to-end test operates a separate initially unpowered research mill, has Sable legitimately deliver one wheat, externally changes the machine to two wheat, powers Create, and requires:
- persistent TAINTED reservation,
- `MILL_PROCESS INVALIDATED ... NO_RESEARCH_CREDIT`,
- two input wheat still present (processing veto),
- otherwise valid standalone unreserved Create processing left operational by separate CI workflow.

## Scope
This is a process-entry **veto**, not a comprehensive input capability interception. It does not block players, belts or hoppers from adding items before the mill attempts processing; it detects certain unauthorized states and preserves evidence. An indistinguishable one-for-one wheat substitution cannot be detected by item-kind/count snapshots. Research unlocks, learning rewards, Outcome Ledger credits and citizen-to-citizen teaching remain disabled. Do not call this guaranteed provenance.

When moving beyond this milestone, instrument or wrap every insertion/extraction route into the reserved mill; then test same-item substitution and exact owner-only insertion, crash recovery and multiplayer red-team cases.
