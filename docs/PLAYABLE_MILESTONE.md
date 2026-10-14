# Hearthbound — First real Minecraft acceptance run

**Status:** Code compiles in Forge CI on ancestor PR #15. This is NOT a verified Minecraft playthrough.

## Requirements
- Minecraft 1.20.1, Java 17 and Forge 47.4.10 as configured in gradle.properties
- Development machine with graphics capable of running Minecraft
- Gradle 8.8 if using the repo's current source directly (no checked-in Gradle wrapper yet)
- Operator permissions when testing commands

## Set up
1. Clone this branch: `git clone -b integration/first-sable-playtest https://github.com/dylandlr/hearthbound.git`
2. In the repository, run `gradle --no-daemon compileJava` and confirm success.
3. Run `gradle --no-daemon runClient`. This launches an actual Forge Minecraft development client, if the local toolchain and graphics environment support it.
4. Create a Creative test world with cheats enabled. The initial mod doesn't include Create integration; no millstone experiment is claimed here.

## First test sequence
1. Run `/hearthbound status`; capture message in screenshot.
2. Run `/sable spawn`. Check real named villager appears and server logs show no exception.
3. Walk 4–10 blocks away; observe movement over 30 seconds. Then move within 3 blocks and confirm stopping.
4. Place two standard chests, fill source with 8 wheat and leave destination empty. Write down coordinates and item counts.
5. Execute `/sable haul <sourceX sourceY sourceZ> <destX destY destZ>`.
6. Run `/sable haul-status`; check progress and final `Haul complete`.
7. Count wheat source + destination + Sable cargo before and after (expected conservation).
8. Repeat with output full. Confirm the source count is unchanged before pickup.
9. Repeat with paused job, `/sable haul-cancel` before pickup, and verify release.
10. Save, exit, reopen. Check `/hearthboundclaims count`, `owner` and job behavior.
11. Repeat in a dedicated server with two connected clients. Never claim multiplayer works solely from single-player testing.

## Pass/fail evidence
Record Minecraft version, Forge version, commit SHA, commands, screenshots/video, error log, source and destination wheat counts, outcome for each numbered step. Gameplay video must be a screen capture of the actual Minecraft process. If a step fails, record it and file an issue.

## Known unsolved limitations
- Untested actual pathfinding; vanilla villager AI competes with path requests.
- No atomic inventory transaction; a crash can cause loss/duplication.
- Reservations may become stale after citizen death; operator repair is manual and potentially unsafe.
- No Create mod dependency, milling, production chain, general job queue, or colony UI.
- CI compiles sources but does not currently perform a real game/client E2E.
