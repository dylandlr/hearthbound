# Live in-game inspection commands v1

On the persistent Forge/Create development server, operators can run:

- `/hearthbound observations` — lists the actual persisted Create milling observations from the overworld SavedData journal, newest first (maximum eight displayed), including authoritative server ticks, dimension, machine block position, recipe, quality and observation UUID.
- `/hearthbound citizens` — reports that no live autonomous citizens or NPC registry are installed. Fixed GameTest citizen UUIDs are not live entities.
- `/hearthbound tasks` — reports that the live server has no citizen task scheduler. Fixture work orders are not live tasks.
- `/hearthbound millstone inspect <pos>` — existing block-level machine diagnostics.
- `/hearthbound status` — existing mod and Create startup report.

New commands are server-side read-only and permission-level 2. The observation journal is diagnostic and is not proof of attribution to a citizen. The commands do not connect to a client camera or start Minecraft on their own.

Next: server-owned citizen entity/task registry with actual movement and work-order execution; report real state through the same commands rather than placeholder counts.
