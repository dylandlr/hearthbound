# First real Hearthbound gameplay footage

**Footage is not yet recorded.** Capture must come from a running Minecraft 1.20.1 Forge client. No rendering, browser recreation, or synthetic clip should be labeled Minecraft gameplay.

## Build under test
- GitHub Actions: https://github.com/dylandlr/hearthbound/actions/runs/38633973345
- Artifact: `hearthbound-minecraft-1.20.1-dev-jar`
- Minecraft: 1.20.1 / Forge: 47.4.10 / Java: 17
- Write the artifact's commit SHA and Minecraft log versions on the footage slate.

## Recording sequence (target 60–120 seconds of uncut evidence)
1. Open Minecraft with the built Hearthbound JAR. Show F3 briefly and `/hearthbound status`.
2. Spawn Sable with `/sable spawn`. Show her custom name and real movement.
3. Place two nearby accessible chests; show a source holding 8 wheat and an empty destination.
4. Assign `/sable haul <source x y z> <destination x y z>`.
5. Follow Sable without camera cuts as she walks to each chest; keep the actual chest inventory changes visible, with a short cut-in inspection only if necessary.
6. Show `/sable haul-status` and the final wheat counts (7 source, 1 destination if exactly one job succeeds).
7. Demonstrate blocked output preflight and the pause/status. Record any unexpected behavior as a **failed test**, not as completed functionality.
8. Save the world and repeat after restart to test persistence, clearly separating footage segments.

## Capture and issue-reporting
- Use OBS Studio Game Capture targeting Minecraft/Java process, 1920x1080, 30 or 60 FPS; record original MP4/MKV and preserve logs.
- Video must include genuine gameplay; do not use a generated animation as evidence.
- Keep errors and UI visible. If villagers fail to path, record the failure and file a GitHub issue with `logs/latest.log`, world seed, coordinates and commit.
- Never claim the Create millstone is working in this video; Create integration is a subsequent milestone.

## Completion gate
Only mark the video task complete when the actual captured video has been reviewed, paired with matching commit SHA, and published via a real URL or attached to the GitHub release.
