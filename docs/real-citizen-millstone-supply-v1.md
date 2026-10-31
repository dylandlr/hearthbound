# Physical citizen arrival followed by real Create wheat supply

The `citizenWalksAndSuppliesMill` Forge GameTest builds unobstructed solid terrain, spawns a real villager tied to a persistent citizen record, and assigns an actual navigation destination adjacent to a Create millstone. After navigation, it checks a persisted server-observed arrival near the worksite and away from the original spawn, then invokes `ServerMillingActions.supplyWheat` to move exactly one wheat from a fixture-owned stack into the actual Create block entity. The test checks conservation and rejects repeat supply.

The movement is genuine server-side villager navigation; the item transfer happens in the GameTest callback, **not by autonomous citizen policy**. The wheat source is a fixture ItemStack, not a persistent citizen inventory, and this test does not power the mill or produce flour. Separate GameTests verify real Create milling outputs and credits. These limitations remain explicit until the complete closed-loop work task is integrated.

Acceptance requires `HEARTHBOUND_CITIZEN_REAL_WALK_SUPPLY_PASS` and a passed `citizen_walks_and_supplies_mill` GameTest. The test result is pending until Minecraft CI runs.
