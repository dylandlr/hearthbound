# Durable citizen work orders v1

The new `DurableCitizenWorkOrder` uses the existing checksummed `DurableOperationIntents` store to prepare a citizen-scoped order with a stable operation ID before any world mutation. A separate adapter can reload the order after server restart without creating a duplicate or assigning it to another citizen. Conflicting recipe/world evidence is rejected by the underlying intent store.

Standalone checks exercise durable identity, restart replay, conflicting evidence and foreign-citizen rejection. No actual Minecraft NPC is driving the work order yet.

**Limitations:** Orders remain unresolved indefinitely and contain no durable execution phase or machine checkpoint linkage. Different citizens can still prepare orders for the same machine; exclusive machine scheduling has not been implemented. An order alone does not authorize resource movement, and this component does not reconcile the machine's physical inventory after a crash. The production adapter must enforce exclusive machine ownership, tie the order ID to the millstone operation, and call the existing fail-closed transfer recovery before retrying anything.

Next: a persisted machine lease/ownership policy, restart reconciliation, and server tick scheduling with an embodied citizen.
