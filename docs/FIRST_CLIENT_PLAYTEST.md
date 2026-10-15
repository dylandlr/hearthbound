# First real Minecraft client playtest — Hearthbound 0.1.0-dev

## Verified artifact
Build: https://github.com/dylandlr/hearthbound/actions/runs/38516720926
Artifact name: `hearthbound-forge-dev-jar` (ZIP containing the built JAR).
Source SHA: `ac86b0d9faa49db0a7c9dbfb85498b9fe9131d42`.
CI outcome: `Forge Compile` passed (`gradle build`, including compilation and JUnit task). **No Minecraft client/server runtime verification yet.**

## Installation
1. Install Minecraft Java Edition **1.20.1** and a matching **Forge 47.4.10** profile through a reputable modded launcher.
2. Download the `hearthbound-forge-dev-jar` artifact from the linked GitHub Actions run and extract its ZIP file.
3. Copy the extracted `hearthbound-0.1.0-dev.jar` (check the actual extracted filename) into the launcher profile's `mods` directory.
4. Use **Java 17** to launch the Minecraft Forge profile. Create is not a runtime dependency for this early barrel test.
5. Create a Creative test world with cheats enabled. Back up worlds before experimenting; this is an unstable development build.

## Commands to attempt
```
/hearthbound status
/hearthbound spawn_sable
/hearthbound assign_sable ~8 ~ ~3
/hearthbound sable_status
/hearthbound cancel_sable
/hearthbound haul_sable ~2 ~ ~ ~10 ~ ~ 4
/hearthbound haul_status
```

For hauling, place two real barrels at the corresponding block positions, with 8 wheat in the source; stand near Sable and ensure walkable ground. Avoid world restarts during an in-flight haul until durable reconciliation has been implemented. Transfer may get stuck; keep this test world disposable.

## Evidence to record
- F3 screen with exact Minecraft/Forge versions and a screenshot showing Sable present.
- `latest.log` or crash report on errors.
- Actual screen capture of the entity moving and inventory counts at pickup/delivery.
- Source/destination coordinates, full observed state, and reproduction steps.

## Release blockers
- Client launch and dedicated server boot have never been exercised in CI.
- No Minecraft GameTests or automated E2E.
- Sable currently uses a persistent tagged vanilla villager, not a custom AI entity.
- Hauling is experimental, with no crash-atomic inventory guarantee.
- Create millstone integration does not yet exist.
- Do not advertise this as a completed colony simulator or authentic gameplay video.
