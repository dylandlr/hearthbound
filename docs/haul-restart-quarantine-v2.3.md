# Hearthbound Forge restart-quarantine integration (v2.3)

Base: `integration/verified-sable-hauling` at `bc7644612868f0a26ba8332094a90e220b2f676b`.

## Implemented in this branch

- New hauling jobs receive a UUID in villager persistent NBT.
- Active job UUIDs are tracked per MinecraftServer instance in memory.
- A cargo-bearing job loaded after server restart (or otherwise unrecognized) is **quarantined** before reaching the inventory insertion path.
- Quarantined jobs remain blocked even when claim recovery fails; `/sable haul-status` exposes the reason.
- `/sable haul-resume` refuses to resume cargo-bearing paused jobs.
- Runtime provenance is cleared at `ServerStoppedEvent`.

## Limitations / safety

This is a fail-closed stopgap, not atomic inventory transfer or automated reconciliation. If a crash happens between insertion and persistence, the system may not be able to distinguish a successful delivery from one that failed. Never auto-retry a quarantined job or manually delete cargo without auditing destination, villager NBT, and any external event journal.

The branch does **not** yet include all code from the separately packaged v1.7-v2.2 artifacts, and does not integrate with the durable receipt journal. The restart guard was deliberately implemented without taking a dependency on those unmerged classes.

## Verification and next tests

54 standalone Java checks in the earlier v2.2 package passed independently. The **modified Forge source in this branch has not yet been compiled against Forge** and no Minecraft dedicated-server restart test has been performed. Next: configure dependency resolution, run Gradle compilation and existing server GameTests, then simulate cargo-bearing save/restart and verify no second insertion.

Intelligent Agents references: Sandholm (2015) on action abstraction, Wellman, Tuyls & Greenwald (2025) on empirical game-theoretic evaluation. They do not provide this recovery protocol.
