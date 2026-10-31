# Physical villager navigation acceptance v1

The `realCitizenPathfinding` Forge GameTest lays a stone path, spawns a tagged Hearthbound villager, persists a MOVE assignment and allows the server-tick navigation controller to move the entity. **No teleport is used to complete this test.** After 230 ticks, the GameTest requires the physical villager to be within two blocks of the target and its citizen registry record to reflect the actual arrived position and IDLE task. The smoke verifier requires `HEARTHBOUND_REAL_CITIZEN_NAVIGATION_PASS`.

This is an acceptance specification, not a claim that pathfinding already passed. Vanilla villager goals may interfere. Keep the failure logs and fix real navigation instead of weakening the acceptance test to a teleport.

The previous `scriptedCitizenMovement` GameTest remains a separate controlled-position persistence test. This new test does not prove inventory pickup, Create interaction, autonomous job selection, or a trained policy.
