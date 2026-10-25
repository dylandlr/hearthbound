# Citizen controller supplies Create millstone after physical navigation

A `MILL_SUPPLY:<worksite BlockPos>` assignment is persisted in the server's citizen registry. The real Minecraft villager is navigated to the worksite by `CitizenMovementObserver`. Once the loaded entity is within two blocks, the server-tick controller (not a GameTest callback) attempts to move exactly one wheat item from the villager's persistent `HearthboundWheat` counter to a real Create millstone immediately east of the worksite. Upon success, the counter decrements and the task transitions to IDLE, logging `HEARTHBOUND_CITIZEN_AUTOMATED_SUPPLY`.

Operators can hold one wheat in the main hand and invoke `/hearthbound mill_supply <citizen-uuid> <x> <y> <z>` where the coordinates identify the walkable worksite immediately west of the millstone. The command removes one wheat from the operator and funds the villager's task; it rejects missing citizens, missing mills, non-idle citizens, and empty hands. This is **scripted, server-side Minecraft behavior**, not deep-learning policy.

The updated `citizenWalksAndSuppliesMill` Forge GameTest no longer invokes `ServerMillingActions.supplyWheat` from its callback: it waits for server-tick controller execution and asserts a one-item millstone input and one-unit villager counter decrement.

Limitations: This v1 `HearthboundWheat` field is a simple entity-NBT resource counter, not a full citizen inventory contract. The resource decrement and Minecraft machine mutation are not crash-atomic, task provenance is not yet tied to a durable operation intent, the operator funds the task, and the controller doesn't power the millstone or collect output. No camera or recording is attached.
