# v0.7.11 — Durable research journal runtime

This branch introduces `ResearchJournalRuntime` as the server-lifetime ownership and lifecycle boundary for the previously tested v0.7.9 `AttributedMillInbox`, `DurableRewardLedger`, and `ResearchReceiptDelivery`.

**Blocked:** this wrapper needs those three exact v0.7.9 Java files imported before the Forge branch can compile. It is intentionally an integration-in-progress PR, not a completed runtime or real Minecraft test.

The runtime supports enqueue of a `VerifiedMillAttribution.Claim`, explicit resource closure and diagnostic readback. Its drain operation is deliberately named `drainUnsafeForStandaloneTestsOnly` and must not be called from live gameplay. The implementation refuses to claim a trusted production reward path until:
- World ID is bound to both append-only journals, with checked headers.
- Journal/world rollback reconciliation is implemented, not caller supplied flags.
- The actual Create process receipt is revalidated for taint immediately before enqueue and before credit.
- Exact inbox and reward-ledger sources are checked in and compiled.
- An actual Forge server and Create millstone GameTest succeeds.

The original standalone package remains available as `hearthbound-durable-research-delivery-v0.7.9.zip`.
