# v0.7.7 — World identity export readiness fence

The new pure Java gate refuses evidence export unless a startup verifier reports all of:
1. Identity existed before the current process started.
2. Identity was read back from persisted world storage and matches in-memory identity.
3. Durable reward/event journal is scoped to the same world identity.
4. Rollback/checkpoint reconciliation succeeded.

This is deliberately an interface contract, **not a claim that those four verifiers exist**. Never set the booleans to constants or permit production export based on the Java unit tests.

## Standalone check
```sh
javac --release 17 -d out src/main/java/dev/hearthbound/evidence/WorldIdentityExportFence.java src/test/java/dev/hearthbound/evidence/WorldIdentityExportFenceTest.java
java -cp out dev.hearthbound.evidence.WorldIdentityExportFenceTest
```

## Remaining work
- Implement true startup file readback and durable checkpoint marker; block export on first boot until restart verification.
- Wire a world-identity header into the v0.7.4 inbox and v0.6 ledger, with recovery/rollback reconciliation.
- Add server-only exporter from `MillProcessReceipts.exportVerified` to the attributed inbox.
- Run Forge build, server test and real millstone test.
- This commit intentionally does not award rewards or unlock technology.
