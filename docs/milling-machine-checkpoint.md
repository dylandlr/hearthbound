# Real millstone intent/checkpoint fixture

The motor GameTest writes a durable intent containing the full input/output ItemStack NBT before enabling the motor. After processing, disconnection and insertion of a fresh wheat item, it records the final inventory and synchronously saves world chunks. A second Minecraft JVM boots that world and verifies:

- The pending operation UUID and complete pre-operation evidence survived.
- Preparing the same intent returns newlyCreated=false.
- The actual reloaded millstone has the exact checkpointed inventory and remains stopped.
- The final inventory differs from the pre-operation inventory.
- Attempting to replace the pending intent with changed inventory fails and preserves the original.

CI requires HEARTHBOUND_MACHINE_CHECKPOINT_PASS in addition to the existing journal restart marker. This tests a clean checkpoint, not a crash between machine and journal writes. Fixture identity uses a unique test incarnation; production world and block-entity identities remain unimplemented. The fixture does not attach its operation ID to the live diagnostic observation or issue rewards. Production intent retirement, reconciliation of torn machine/journal checkpoints, and credit integration remain outstanding.
