# Isolated crash probe v3 — saved baseline first

The manual-only crash workflow now runs a complete normal Minecraft GameTest cycle **before** injecting any fault. It verifies all required GameTest markers, checks that exactly one saved GameTest world exists, makes an archival copy of the saved world, and records a SHA-256 hash of that archive.

The workflow restores the saved baseline from the archive to the disposable `run-gametest` directory, launches the server again with the post-attempt hard-halt injection, and then attempts a second-JVM restart using the resulting world. It will fail if the baseline test did not exit cleanly or if the world archive is incomplete.

This setup distinguishes lack of an initial `level.dat` from a genuinely non-restartable crashed world. The baseline remains an immutable CI artifact for forensic comparison, while the disposable restored copy may be changed by the crash probe.

**Caveats:** This workflow has not yet been manually dispatched or verified. Re-running Minecraft GameTests in a saved baseline world can cause fixture conflicts or reset GameTest structures, so the first execution must inspect the resulting logs before accepting any inventory conclusions. The current restart probe checks journal existence and no successful delivery log; it does not validate full entity/millstone inventory consistency after the crash. Exactly-once guarantees remain unproven.
