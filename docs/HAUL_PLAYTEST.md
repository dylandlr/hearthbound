# Sable first hauling job (experimental)

This is a **real Minecraft-side implementation proposal**, not proof of a running client. It is stacked on PR #7 and #6.

## In-game playtest (operator commands)
1. Place two standard single chests on level terrain with accessible walking paths, within 16 blocks of Sable.
2. Put wheat in the source chest and leave room in the destination.
3. Run `/sable spawn` if necessary.
4. Run `/sable haul <source x y z> <destination x y z>`, using the chest block positions.
5. Watch Sable walk to the source, retrieve one wheat, walk to destination, and deposit it.
6. Run `/sable haul-status`; expected result: `Haul complete`.
7. Repeat with empty source or full output and observe `Paused`. Fix the issue and use `/sable haul-resume`.
8. Repeat with a Minecraft save/restart during each phase and count every item before/after.
9. Run with two players and log TPS / number of navigations.

## Explicit limitations
- Experimental single-item job; **not safe for valuable resources**. Chest and citizen are not persisted in one atomic transaction; crash duplication/loss remains possible.
- The initial job assignment and status commands require operator privileges. Citizens are selected within 16 blocks.
- Vanilla villager behavior may override pathfinding; Minecraft client E2E validation is outstanding.
- No inventory reservation among multiple citizens, workshop ownership, Create milling, or robust chunk-unload recovery yet.
- Pure-Java CI **cannot compile the Forge-dependent world code**. A pinned Forge build and game test pipeline are still required.
