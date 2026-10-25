# Citizen supply saved-world restart verification v2

The second-JVM restart verifier now loads the worksite's Minecraft chunk and the chunk containing the citizen's location recorded at the end of the GameTest. It resolves the actual tagged villager and compares the persisted wheat balance, operation-linked delivery receipt, and machine position against the expectation file and durable work-order record. It separately examines the **actual reloaded Create millstone** and demands one wheat in its input slot, alongside the previously required persistent outstanding supply task and write-ahead attempt.

CI requires `HEARTHBOUND_CITIZEN_SUPPLY_WORLD_RESTART_PASS` in the second-process server log. Missing entities, incorrect resource balances or absent Create input fail acceptance. This is a new test specification and does not count as verified until the separate JVM successfully passes.

Remaining limits: Tests cover a normal restart after a completed delivery and an intentionally blocked second task, not a forced crash between individual writes. Automatic reconciliation and exactly-once crash guarantees are not established.
