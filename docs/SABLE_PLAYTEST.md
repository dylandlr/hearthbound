# First Sable Minecraft Playtest

## Status and prerequisites
This is a narrow integration experiment stacked on PR #6. Java-only policy CI is not a Forge compilation test. Forge client/server boot, navigation and mod compatibility remain **unverified** until a real dev environment run.

## Manual acceptance
1. Start a Minecraft 1.20.1 Forge 47.4.10 development server with the Hearthbound mod built from this branch.
2. Join with an operator account and execute `/sable spawn` on land.
3. Verify a real villager named **Sable** appears, not an armor stand or rendered mockup.
4. Walk more than three blocks but remain within twelve blocks. Sable should attempt to navigate toward you (navigation remains subject to vanilla pathfinding and villager brain behavior).
5. Approach within three blocks; check navigation stops.
6. Walk beyond twelve blocks; check Sable does not chase indefinitely.
7. Restart server and verify Sable retains her custom name and marker. Verify that she can follow again.
8. Join with a second player and observe nearest-player targeting; repeat after player logout.
9. Try `/sable spawn` without operator permission: it must be rejected.
10. Check server log for errors and collect a real client capture with Minecraft and mod versions visible.

## Known omissions
- Not a full custom entity; uses a tagged vanilla villager.
- Minecraft villager AI can compete with the navigation goal; dedicated goals will be needed.
- No Create dependency, workshop, inventory hauling, job reservation or persistent task state.
- No claim of completed E2E test or gameplay video.
- Additional spawns are currently allowed and should eventually be controlled per colony.
