# Isolated crash experiment: machine-state proof

The second JVM crash probe now reads the exact crash operation's checksummed attempt, extracts the recorded citizen UUID, dimension and millstone position, loads the actual Forge/Create block entity from the saved world, and verifies that the **input slot is empty** following an injected crash immediately before mutation. If the citizen still exists in the persistent registry, the probe also rejects a completed (`IDLE`) task for that interrupted operation. The manual workflow requires `HEARTHBOUND_CRASH_RESTART_MACHINE_PASS` for the exact UUID.

This expands beyond journal existence, but it deliberately does not assert that the villager entity survived a hard crash: an unsaved entity may be absent. Nor does it prove exactly-once settlement. The baseline GameTest re-run could reset the millstone fixture; only a completed real crash execution can establish that this test arrangement works. Failure to find the millstone is a genuine test failure, not a reason to synthesize it on restart.

The workflow is still manual-only and has not been dispatched through this connection. CI compilation tests do not imply the abrupt crash experiment passed.
