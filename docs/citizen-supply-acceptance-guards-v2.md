# Citizen milling supply acceptance guards v2

The Minecraft GameTest for the server-tick milling-supply controller now checks, before the villager can reach the worksite, that the Create millstone input remains empty and the citizen's entity-NBT wheat balance remains at two. At the completion checkpoint it requires a genuine server-observed arrival, exactly one wheat in the millstone, exactly one wheat remaining with the citizen, and an IDLE task. These guardrails are meant to detect early transfers, resource duplication and repeated work.

This is **not yet a crash-safe two-phase inventory transaction**. The entity's NBT counter, block-entity mutation and registry completion can be interrupted independently if Minecraft crashes. A durable operation journal with reconciliation and a persisted pre-operation assignment is still necessary. Existing tests validate live gameplay and normal restarts, not fault injection at every write boundary.

The acceptance CI verifies the old multi-operation research evidence and the new server-tick supply test independently. Do not interpret passing a test as evidence that full Create processing or autonomous training has been integrated into the citizen work loop.
