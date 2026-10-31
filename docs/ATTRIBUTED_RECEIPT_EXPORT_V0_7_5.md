# v0.7.5 — Attributed Minecraft receipt export

This branch extends v0.7.3 and the existing Create millstone mixin with a fail-closed `MillProcessReceipts.exportVerified` method, returning a pure Java `VerifiedMillAttribution.Claim`.

## Provenance requirements
- Server-side real `process()` receipt, validated against citizen, job, machine and active reservation.
- Unexpired, untainted job with recorded authorized processing and strictly ordered observed start/completion ticks.
- Recipe evidence consistent with one wheat consumed and flour produced.
- **Durable per-save world UUID supplied by caller**. Do not generate a random world ID on export/recovery.

## Deliberately not completed
- The v0.7.4 `AttributedMillInbox` and v0.6 `DurableRewardLedger` are **not yet copied into this Minecraft module**.
- No tick-event exporter, acknowledgement worker, automatic research credit, or restart reconciliation is installed.
- A late taint after receipt capture must prevent downstream reward delivery; the durable pipeline needs reconciliation with authoritative reservation state.
- No Forge build/GameTest/live client has been run.

## Standalone checks
```sh
javac --release 17 -d out src/main/java/dev/hearthbound/evidence/VerifiedMillAttribution.java src/test/java/dev/hearthbound/evidence/VerifiedMillAttributionTest.java
java -cp out dev.hearthbound.evidence.VerifiedMillAttributionTest
```

## Next integration sequence
1. Persist a per-world identity with Minecraft `SavedData` and test restart identity stability.
2. Reuse v0.7.4 attributed inbox and v0.6 idempotent reward journal in the authoritative server.
3. Export only verified and untainted receipts, enqueue before credit, credit idempotently, then ACK.
4. Handle taint races, journal crash windows, world rollbacks, and outstanding ACK replay.
5. Verify an actual powered Create millstone in a client/server test before claiming gameplay integration.
