# Crash restart verifier: entity-load gate

The isolated hard-crash verifier previously ran in `ServerStartedEvent`, immediately after the server started. That is too early to assert that persisted villagers are missing: Minecraft loads nearby entities as chunks are brought into service. The verifier now runs once at the end of server tick 80, before forcing the millstone chunk(s) into memory and locating the original citizen. A missing villager remains a real failure, not a reason to invent or respawn one.

The crash workflow remains manual-only because it intentionally hard-terminates a disposable Minecraft server. Normal Forge integration tests do not prove this crash/restart phase works. The first actual run must still be triggered in GitHub Actions by a user who accepts the two acknowledgments.
