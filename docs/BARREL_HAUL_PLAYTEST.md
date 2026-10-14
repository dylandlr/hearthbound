# Minecraft barrel-to-barrel hauling probe

## Objective
Sable physically walks to a vanilla barrel, extracts wheat from its real inventory, retains a persisted abstract cargo count, and walks to a second vanilla barrel to insert it. This is an **experimental Forge source implementation**; it has not passed a Forge client compile or runtime test.

## Commands
With cheats/op enabled, create two loaded barrels, put 8 wheat in the source, and stand near a tagged Sable:

```mcfunction
/hearthbound spawn_sable
/hearthbound haul_sable <sourceX> <sourceY> <sourceZ> <destX> <destY> <destZ> 4
/hearthbound haul_status
```

Use the vanilla Brigadier block-position syntax, e.g.
```mcfunction
/hearthbound haul_sable ~2 ~ ~ ~10 ~ ~ 4
```
These are **barrel block coordinates**, not standing coordinates.

## Expected normal case
- Sable walks to source; no inventory extraction occurs until within reach.
- Sable withdraws at most four real wheat into persisted cargo. Source barrel decreases.
- Sable walks to destination and deposits the carried wheat. Destination increases.
- `haul_status` shows phases and carried count while active, then completion.
- Total wheat across source + carried + destination stays constant.

## Fault cases
- Empty source: NO_WHEAT, no extraction.
- Full destination before pickup: OUTPUT_FULL, no extraction.
- Full destination after pickup: OUTPUT_FULL_CARRYING, cargo remains associated with Sable.
- Block removed: MISSING_BARREL; cargo must not be discarded.
- Chunk unload: pause; no force-loaded chunk access.
- No new task can overwrite Sable's active cargo.
- Test unload/reload, death, blocked route, save/restart, and 2-player concurrent commands separately.

## Known limitations — must fix before claiming production-safe transport
1. Source barrel and Sable entity NBT do **not** share an atomic save transaction. Power loss or forced crash between saving the barrel and citizen could duplicate or lose cargo. A world-level journal with recovery is required.
2. The current prototype carries an integer wheat count in persisted NBT rather than a visible held-item model. Improve animation and carried inventory after correctness is proven.
3. No multi-colony reservation manager yet. Concurrent unrelated systems could change the same barrels; guard these with explicit reservations.
4. This is only vanilla **wheat** and vanilla **barrels**, not Create milling, recipes, or logistics.
5. It depends on the prior Sable spawn command and has not been ForgeGradle compiled.
6. Pathfinding can fail indefinitely during hauling; integrate the bounded navigation watchdog from TravelProgress before testing failure outcomes.
7. No automatic safe return/reassignment of in-flight cargo, no durable audit log, and no real GUI yet.

## Production acceptance gates
- Verify full Forge build and in-game visual movement.
- Confirm 4 source wheat removed, exactly 4 delivered, and no phantom cargo.
- Run fault cases, concurrent orders, and crash/restart recovery.
- Capture real Minecraft client video showing entire transfer.
- Only then bridge to a real powered Create millstone.

## Navigation and arbitration update
- Travel assignments are rejected while hauling is active; travel cancellation also refuses to overwrite hauling cargo.
- The hauling controller now pauses the job on STALLED/TIMED_OUT instead of navigating forever, and reports the retained cargo count.
- **No resume/recover command exists yet.** Paused tasks stay assigned until a tested reconciliation procedure is added; do not remove the villager or edit NBT to clear cargo.
- Navigation progress tracking is currently in-memory and restarts on chunk load/restart. The job and cargo remain persisted, but this is not crash-atomicity.
- A real Minecraft/Forge compile and playtest remain mandatory before merging this PR.
