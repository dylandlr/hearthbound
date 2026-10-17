# Hearthbound v0.7.2 — opt-in autonomous two-job experiment

SableAutoWork persists operator-configured source, destination and library
locations in the villager's NBT, defaults OFF, and revisits choices at
UUID-staggered 200-game-tick boundaries. Declined offers trigger a 600-tick
cooldown. The controller calls it every villager tick so staggered decisions
cannot be skipped by a 20-tick movement gate. No chunks are force-loaded.

## Operator setup
1. /sable spawn
2. /hearthbound library primer
3. Put the marked primer in the library chest and wheat in a source inventory.
4. /sable auto-work-config <source x y z> <destination x y z> <library x y z>
5. /sable haul-priority 1
6. /hearthbound library priority 4
7. /sable auto-work-on
8. /sable auto-work-status
9. /sable auto-work-off

Reverse priorities to bias studying. Only one automatic loop is permitted:
LibraryAutonomyTick refuses to run while SableAutoWork is enabled; enabling
auto work also turns off standalone library auto study.

## Limits and regression gates
- This is an opt-in, fixed-endpoint test routine, not a colony job-board.
- The two physical executors still have separate ownership implementations,
  and the haul executor must enforce source claims, mill reservations, and cargo
  quarantine before mutating inventories.
- A loaded endpoint does NOT guarantee valid wheat, acceptance, or a reachable path.
- No fallback to a second candidate if the chosen executor declines.
- Quarantined/paused cargo blocks new assignments until safely reconciled.
- Sable's policy still receives placeholder 0 needs values; those are NOT real
  danger, hunger or fatigue observations.
- The dispatcher trace is persisted only as the last choice record.
- The citizen must remain loaded and be the designated Sable test villager.
- Verify actual Forge compilation, commands, moving citizen, persistence after
  restart, no competing navigation, and full item conservation before shipping.
- This commit does not claim gameplay or CI tests were executed.
