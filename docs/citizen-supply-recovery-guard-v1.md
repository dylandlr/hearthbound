# Citizen supply fail-closed guard

Minecraft acceptance run 40232852759 succeeded for the first controller-triggered Create wheat supply. This follow-up explicitly guards the case where a millstone input is occupied when a citizen with wheat is assigned a new delivery.

The server-tick controller refuses to debit the citizen wheat counter or finish the new task while the mill contains an input. It retains `MILL_SUPPLY` for operator intervention/recovery and logs a throttled blocked-work warning. Successful delivery also records its mill position and logical tick in the villager's persistent entity data, while the citizen work-order state remains in SavedData.

The extended live GameTest verifies an initial physical walk and wheat transfer, durable-NBT round-trip of the completed task, then reassigns a second delivery against an occupied input. It asserts that no second wheat is removed and the blocked task remains outstanding.

**This is an observability and resource-loss prevention increment, not atomic crash recovery**. The millstone block entity, villager NBT, and citizen SavedData are not committed as one database transaction. Interruptions between updates can still produce ambiguous states. A precommitted operation ID and replay/reconciliation protocol remain necessary before claiming exactly-once crash guarantees.
