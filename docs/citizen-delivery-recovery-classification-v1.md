# Citizen delivery recovery decision contract v1

The newly added `CitizenSupplyRecovery` pure decision contract distinguishes a missing attempt from a known write-ahead attempt, a matching completed-operation receipt and an ambiguous interruption. For any durable attempt without a matching operation receipt, the decision is `AMBIGUOUS_BLOCKED`: the server **must not** replay a wheat transfer based solely on a wheat count or millstone contents.

A matching receipt, an IDLE task and a one-unit citizen wheat debit can classify the operation as `COMPLETED_OBSERVED`. Machine input need not still be wheat if Create has already consumed it. This is an evidence classification only, not automatic post-crash reconciliation or settlement. The current villager metadata is not yet a transactionally persisted commit receipt; this contract is a prerequisite for a future actual recovery service.

The Forge GameTest `citizenSupplyRecoveryContract` covers matching completion, pre-mutation interruption and mismatched/missing receipt cases. It must be present in the acceptance log before this milestone is declared verified.
