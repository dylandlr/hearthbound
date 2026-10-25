# Durable citizen wheat reservations v1

The new `DurableCitizenInventory` records one-wheat operation debits in an append-only checksummed ledger and derives remaining stock from those persisted debits. The `DurableCreditLedger.find(operationId)` read permits an identical retry even when the stock was exhausted, while rejecting a fresh overdraw. Standalone contracts verify first debit, reload, identical retry and depletion.

**Important constraints:** initial stock is still provided by the caller, not by a persistent citizen entity. A credit-ledger debit is not an atomic transfer to Create's block entity. Interrupted transfers must reconcile the saved machine input against the operation before retrying, not recreate the wheat. Multiple independent inventory instances must not concurrently authorize the same last item through the separate balance-and-commit steps; production needs a single locked reserve/check transaction. No production NPC inventory or autonomous agent is claimed.

Next: introduce a single atomic reservation ledger API and an explicit machine reconciliation state, then connect it through server-owned NPC work orders.
