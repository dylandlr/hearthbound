# First live operation-window attribution in Create GameTest

Before energizing the motor, the fixture now records the server's authoritative logical start tick with the operation, citizen and machine key. At completed milling checkpoint it searches the SavedData journal within the durable start and current logical tick, requires exactly one matching real Create mutation, and durably commits the mutation's observed tick as the end of that operation's window. Only after this operation-specific selection can the existing receipt and citizen credit validation run.

After Minecraft restarts, the fixture reloads the complete durable window and resolves the identical real observation by dimension, position, and persisted start/end ticks. The original receipt and credit idempotence tests remain in force; CI archives start and completion ledgers for inspection.

No automatic recovery from an incomplete operation window is claimed. The test still executes **one actual wheat milling operation** and subsequently transfers machine ownership; it does not yet execute a second actual milling operation or implement a continuous NPC scheduler.
