# Crash experiment v8 — save the actual pre-attempt world

Before writing a delivery attempt in the deliberately isolated `after_attempt_before_mutation` crash stage, the Minecraft server now synchronously saves its current world state, including the real villager and Create millstone. Only then does the citizen supply controller write the fsync-protected delivery intent and abruptly halt the JVM before mutating the Create input.

The manual-only crash workflow requires `HEARTHBOUND_FAULT_PRE_ATTEMPT_WORLD_SAVED` before `HEARTHBOUND_FAULT_INJECTION_AFTER_ATTEMPT`, and its second JVM still verifies the exact attempt, empty Create input, and original villager's two wheat with no receipt. The saved baseline in the same process is key: a previous completed GameTest run cannot guarantee that a newly spawned fixture citizen is present on disk.

**Scope limitation:** A deliberate synchronous save immediately before the fault improves repeatability but narrows the test to one precise crash boundary. It cannot demonstrate durability of changes that were still buffered at time of failure, nor safely settle an ambiguous post-mutation operation. The destructive workflow remains manually dispatched, not tested by ordinary Forge CI.
