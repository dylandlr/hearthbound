# v0.7.10 — Forge lifecycle observer (fail-closed)

This is the **first direct Forge startup hook** for the durable identity checkpoint.
On `ServerStartedEvent`, it reads `HearthboundWorldIdentity` from Overworld SavedData
and checks an independent identity marker in the world `data/` directory.

It intentionally **never enables research export**: neither journal ownership nor
world rollback reconciliation is currently proved. The log reports
`HEARTHBOUND_RESEARCH_STARTUP` and status remains `EXPORT_DISABLED`.

## Operational notes
- First boot writes a marker and returns RESTART_REQUIRED.
- Subsequent startup can confirm the marker's world UUID but still reports
  `ROLLBACK_UNVERIFIED` until a genuine reconciliation implementation exists.
- Stopping a server invalidates the in-process diagnostic state.
- Uses Forge `ServerStartedEvent` and `ServerStoppingEvent` on Forge event bus.
- Does not deliver inbox events, issue rewards, or alter Create machinery.
- World rollback and journal-directory naming remain **not fully implemented**.
- Java/Forge compile and real server smoke test still required.
- A backup/rollback mismatch can only be detected once durable journal headers
  and monotonic checkpoint state have been implemented.

## Next
1. Import previously tested `AttributedMillInbox` and `DurableRewardLedger`.
2. Add durable world ID headers and reconcile journal identity at server startup.
3. Bind the verified receipt exporter to enqueue under a real readiness token.
4. Drain idempotently on the authoritative server thread and run Forge GameTests.
