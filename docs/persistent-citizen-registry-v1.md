# Server-owned citizen registry v1

`CitizenRegistrySavedData` stores citizen UUID, display name, dimension, block position, task placeholder, and last-updated logical server tick in the overworld SavedData. An operator may create a record in-game using `/hearthbound citizen create` while standing at its intended position. `/hearthbound citizens` lists the actual records, and `/hearthbound tasks` counts non-idle persisted task records (initial records are IDLE). All commands require permission level 2.

This is an **identity registry, not a Minecraft entity**: no NPC is spawned and no autonomous movement, inventory, AI training or decision-loop scheduling is connected yet. The operator command does not pretend otherwise. Existing diagnostic milling observations remain separate.

A Forge GameTest asserts registry identity and NBT serialization. The Minecraft acceptance workflow requires `HEARTHBOUND_GAMETEST_PASS persistent_citizen_registry` in the real server log.

Next: introduce a physical citizen entity (or safe temporary villager-backed embodiment), lifecycle synchronization with the registry, and server tick observation/action boundaries. Only then should citizen positions and tasks be presented as live state.
