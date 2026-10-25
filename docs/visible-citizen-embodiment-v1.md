# Visible Hearthbound citizen embodiment v1

The operator command `/hearthbound citizen create` now creates a registry record and spawns a visible vanilla villager in the Minecraft world. The villager retains the citizen UUID in Forge's persistent entity NBT (key `HearthboundCitizenId`) and can be found again among loaded server entities. This is a temporary visible avatar; not a custom NPC implementation.

A Forge GameTest asserts a real entity is spawned, has the UUID in persistent NBT, and can be looked up by that ID. The acceptance checker requires `HEARTHBOUND_GAMETEST_PASS visible_citizen_embodiment`.

**Boundaries:** Villagers use vanilla Minecraft AI, not Hearthbound task decisions, inventory reservations, movement, reproduction or policy training. Registrations and entity spawning are not a single crash-atomic transaction, so a crash may leave registry/entity mismatch; reconciliation is future work. Lookup covers loaded entities only. Registry position is initial position, not a live synchronization. In-game observations are not yet recordings or rendered POVs.
