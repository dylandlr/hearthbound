# Hearthbound Library Autonomous Study v0.5.2

## Server-side travel-to-study vertical slice
An operator assigns an existing villager to a library container. The villager
navigates using Minecraft's pathfinding. Once adjacent, the agent initiates the
existing physically validated study session. No teleportation or instant learning.

The job is opt-in, respects hauling ownership, times out after 2400 game ticks,
does not force-load distant chunks, and interrupts on dimension mismatch or
conflicting hauling tasks. Existing study validation still checks physical book
presence every tick.

## Development controls
`/hearthbound library assign <shelf blockpos>` — nearest villager within 8
blocks receives autonomous pathfinding study job. The container must be loaded.
`/hearthbound library inspect` — inspect state and knowledge.

## Limitations and next work
This is assignment-driven navigation rather than an independently discovered
library preference. No literacy traits, workplace scheduling, borrowing system,
multi-book content registry hook, library policy, or mod-guidebook lesson mapping
exists in this vertical slice. NPC pathfinding and collision require a real
Minecraft integration test. No claim of end-to-end tests passing is made.
