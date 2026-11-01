# v0.7.9 — Research delivery admission

This change builds on v0.7.8 and adds a **fail-closed admission check** that combines a disk-backed startup marker, world identity matching, and validated citizen/machine attribution.

The previous standalone v0.7.9 `ResearchReceiptDelivery` still uses caller-supplied booleans and remains a **local package**, not yet wired into Forge. This PR does not pretend the coordinator and journals have been imported.

## Run standalone checks
```sh
javac --release 17 -d out \
  src/main/java/dev/hearthbound/evidence/{WorldStartupCheckpoint,WorldIdentityExportFence,VerifiedMillAttribution,ResearchExportAdmission}.java \
  src/test/java/dev/hearthbound/evidence/ResearchExportAdmissionTest.java
java -cp out dev.hearthbound.evidence.ResearchExportAdmissionTest
```

## Critical remaining work
- Replace externally supplied startup evidence with concrete verifier reading saved-data identity and **actual** durable journal world headers; currently caller assertions can be untrustworthy.
- Implement real rollback detection; a boolean by itself is not rollback detection.
- Import v0.7.9 ledger/inbox/coordinator into Forge and connect the verified Create callback on the server thread.
- Integrate event admission after initialization and before durable enqueue; invalidate tainted entries before reward credit.
- Test real Forge startup, restart, one physical Create milling event, journal recovery, and denial paths.

No in-game research credits are enabled by this PR.
