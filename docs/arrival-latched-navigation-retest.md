# Arrival-latched navigation retest

In Minecraft acceptance #40228591357, the villager physically arrived within one block of its assigned worksite, and the server persisted its IDLE task and observed arrival position. Vanilla AI subsequently wandered two blocks away before the fixed-delay final assertion, causing an incorrect failure. The updated GameTest verifies that the **server-observed, recorded arrival** is within two blocks of the target and more than two blocks from the origin; it no longer requires the villager to remain still after task completion. The pass marker reports the recorded arrival, not the later location. No teleport or artificially assigned arrival is used in the real-navigation GameTest.

A separate server-side observation is essential for provenance. This milestone does not prove interaction with the worksite or continued position synchronization after the task becomes IDLE.
