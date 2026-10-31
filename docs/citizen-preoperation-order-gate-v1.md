# Citizen milling pre-operation durable assignment gate

`CitizenSupplyAssignment` bridges the existing durable citizen work-order journal to Forge/Create milling. A citizen/machine/dimension/recipe identity is persisted before the operator command funds and assigns the task; the server-tick controller requires a recovered matching order before moving a wheat item into the Create millstone.

The live GameTest now explicitly tests that an unprepared identity is denied and a prepared identity is accepted. It still verifies the villager's real arrival, one-wheat transfer, and occupied-machine fail-closed behavior.

**Current limitation:** This journal establishes durable pre-operation authorization, not a crash-atomic machine/citizen transfer. It does not contain a durable transfer completion receipt or recover the precise order of NBT persistence across machine, entity and registry stores. Work-order retirement and machine handoff remain separate problems. Do not interpret this milestone as exactly-once crash recovery.
