# Atomic bounded wheat reservation and transfer recovery v2

The durable ledger now provides `commitBounded(Credit, maximumBalance)`: an operation replay check, total-balance calculation, cap enforcement and append are performed under the **same OS file lock**. `DurableCitizenInventory.reserve` uses this method, so two separate controllers cannot both commit an additional last-wheat debit by doing a stale read followed by a later write. Replays of the same operation remain idempotent even at zero stock.

A separate `WheatTransferRecovery` policy treats a debit without a verified, durable matching machine checkpoint as **QUARANTINE**, not permission to recreate wheat. Only matching operation/citizen ownership and a durable unprocessed machine-input checkpoint allow CONFIRMED_INSERTED. This is a conservative pure-Java decision policy, **not** yet a live game-world reconciliation implementation.

## Remaining limitations

* The ledger protects a single process/host/filesystem supporting its locking semantics; concurrent threads in the same JVM may receive `OverlappingFileLockException` rather than wait, and need an outer serialization policy. This is not proof of multi-host distributed locking.
* The citizen's initial wheat quantity is supplied to the adapter and is not itself a durable, auditable acquisition record. Do not present it as a full persistent inventory.
* A disk ledger debit and a Create block-entity insertion are not one atomic transaction. A crash can leave an unresolved transfer; recovery must quarantine and reconcile, never grant a second item.
* The GameTest is still scripted with a fixture stack. Neither an embodied NPC nor automatic world restart reconciliation has been implemented.

CI runs the bounded reservation and fail-closed reconciliation contracts, in addition to the existing Forge compilation tests.
