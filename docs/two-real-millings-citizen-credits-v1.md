# Real Create milling with two isolated citizen credits

The `consecutiveRealMillings` Forge GameTest drives **two actual Create millstone processing calls on one block entity**. Each real output observation now produces an isolated fixture research-credit transaction under a distinct operation UUID and fixture citizen (081 and 082). The operation-to-observation receipt is replay-idempotent.

A separate restarted Minecraft process reloads both real observation IDs from the SavedData journal and both research balances from the durable ledger. It must reject duplicate awards for both operations and log `HEARTHBOUND_TWO_CITIZEN_REAL_CREDITS_RESTART_PASS`. The acceptance workflow checks this marker, the expected NBT fixture and credit-ledger evidence.

**Scope boundary:** these are two scripted GameTest fixture identities, not two embodied NPCs, and their assignments are reconstructed from observed evidence rather than independently persisted before each machine mutation. Unlike the earlier one-operation gate, this is not yet production-grade citizen attribution. The next step is to bind each operation to a pre-mutation persisted citizen assignment and machine generation and verify exclusive ownership from both cycles. No autonomous scheduling or learning is claimed.
