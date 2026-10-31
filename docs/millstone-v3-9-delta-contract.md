# Hearthbound v3.9 — Inventory-delta contract

Added a pure Java `InventoryDelta.compare` utility and its contract tests. It classifies slot changes as `POSITIVE_DELTAS`, `NONE_OBSERVED`, or `AMBIGUOUS`, without awarding rewards. Incompatible item replacements, slot removals, and decreases must fail closed instead of silently disappearing from the evidence stream.

This utility is intentionally not yet wired into `MillstoneMutationAudit`. Minecraft ItemStack identity includes components/NBT not captured by the utility's simple item ID; a production adapter must compare full stack equivalence and avoid misclassifying item variant replacements. The diagnostic mutation observer continues to use its current implementation until that adapter is available.

The new test suite is included in CI's Java contract job and Forge test source compilation. A passing build validates these pure Java cases, not a real Minecraft recipe or Mixin injection.

Research credit remains disabled. Dedicated-server startup still requires explicit EULA acceptance; no runtime success is claimed.
