# First Mill hauling contract — phase 1

The pure Java `TransferLedger` models a single logical batch through PLANNED → WITHDRAWN → DELIVERED, or PLANNED → CANCELLED.

## Invariants
- The same ledger cannot withdraw twice or deliver twice.
- Cargo that has already been withdrawn cannot be cancelled by simply dropping the task; the server must explicitly return it, deliver it, or reconcile it.
- A restored ledger is **not proof** of physical inventory state. On restart, reconcile persisted source, destination, citizen cargo and transaction id first.
- Item conservation must be checked at the Minecraft adapter boundary against real inventory counts; ledger transitions alone do not move or reserve items.

## Physical adapter acceptance (not implemented)
1. Reserve exact source item stack quantity and target capacity on the Minecraft server.
2. Extract real items; persist carried cargo and ledger state together as robustly as the platform allows.
3. Move the physical villager with cargo while preserving ownership across unload/restart.
4. Insert exactly the verified carried items into the destination; deliver only on confirmed completion.
5. At any failure, perform reconciliation rather than blindly replay extraction.
6. Add property-based and game-runtime duplication tests for cancellation, forced chunk unload, output-full, disconnect, crash and restart.

## Local Java smoke test
```sh
mkdir -p build/policy-classes
javac --release 17 -d build/policy-classes src/main/java/dev/hearthbound/jobs/TransferLedger.java src/test/java/dev/hearthbound/jobs/TransferLedgerSmokeTest.java
java -cp build/policy-classes dev.hearthbound.jobs.TransferLedgerSmokeTest
```

This is not a Minecraft hauling implementation or actual gameplay footage.
