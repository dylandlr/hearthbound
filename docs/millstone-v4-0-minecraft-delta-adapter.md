# Hearthbound v4.0 — ItemStack identity-aware millstone deltas

The Create processing boundary now uses `MinecraftInventoryDelta.compare`, a Minecraft-specific adapter that compares the full `ItemStack.isSameItemSameTags` identity before treating a count increase as produced items. Changed NBT, item replacement, slot removal, and count decrease are classified as `ambiguous`. This adapter is now wired directly into `MillstoneMutationAudit.after`.

The pure-Java `InventoryDelta` contract remains a baseline. The Minecraft-specific adapter does not claim that a positive net delta is an authoritative receipt, nor can it prove that every rolled item was inserted when output inventories are full. Receipts and citizen research credit remain disabled.

Next: verify Forge CI, add Minecraft runtime tests for NBT-sensitive transitions, verify Mixin injection via EULA-authorized dedicated server, and persist mutation evidence with an exactly-once event sequence only after actual runtime observation.
