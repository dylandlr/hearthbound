# First Hearthbound citizen movement loop

The persistent citizen registry now accepts a `MOVE:<packed BlockPos>` task. An operator can use:

```
/hearthbound citizen create
/hearthbound citizens
/hearthbound move <citizen-uuid> <x> <y> <z>
/hearthbound tasks
```

Every ten logical server ticks, `CitizenMovementObserver` attempts navigation of the loaded villager bearing that persistent citizen UUID toward its designated target. The observer updates the registry using the **real villager position**, not a predicted position. When the entity is within two blocks, the task becomes IDLE and an arrival marker is logged.

The first Forge GameTest proves the assignment is saved, the entity's position is recorded, the task completes and those values round-trip through NBT. **The GameTest moves the villager to the target programmatically and does not prove pathfinding succeeded on its own.** A separate live server test must verify navigation across walkable terrain and chunk unload/reload conditions.

Limitations: this first implementation scans loaded villagers; there is no dedicated custom entity type, pathfinding success tracking, timeout, true continuously synchronized idle positions, physical resource transport, scheduler arbitration, or neural policy. The world registry still needs authoritative restoration of entities after crash/spawn mismatch. Navigation may be superseded by vanilla villager AI and is not claimed as reliable autonomous behavior yet.
