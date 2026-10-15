# Hearthbound

A Minecraft-first, fun-first Create-powered AI colony simulator.

The First Mill prototype runs in Minecraft 1.20.1 with Forge 47.4.10 and optional Create 6.0.8. Sable can travel, carry wheat into a powered millstone, and collect flour under a persistent work order with a stockpile target. Workers show their cargo, pause for station transfers, and return to a saved workshop waiting spot between jobs. See the [workshop routine](docs/WORKSHOP_ROUTINE.md) for controls and behavior.

Current development is on `feature/first-mill-foundation`. Start with [development status](docs/DEVELOPMENT_STATUS.md) and the [real client playtest record](docs/REAL_CLIENT_PLAYTEST_2026-10-14.md). Earlier documents retain their historical validation limits.

With an empty hand, right-click Sable to select workshop stations in the world, set a flour target, and start, stop or resume work. See [in-game workshop controls](docs/WORKSHOP_CONTROLS.md).

Workshops keep a mill owner and reserve both hauling endpoints until delivery finishes. Multiple workers can share equipment without planning conflicting hauls; stopped or unloaded workers retain cargo and their reservations. See [shared workshops](docs/WORKSHOP_SHARING.md).
