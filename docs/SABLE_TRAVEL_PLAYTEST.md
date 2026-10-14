# Sable travel-job playtest — Minecraft-only

## Purpose
This is the first in-game physical job probe. A specially tagged persistent vanilla villager should walk toward a loaded, reachable destination and stop within approximately two blocks. This does not yet transport inventory or interact with Create.

## Commands
Use an operator/cheats-enabled Minecraft Forge 1.20.1 development world:

```mcfunction
/hearthbound status
/hearthbound spawn_sable
/hearthbound assign_sable ~8 ~ ~3
/hearthbound cancel_sable
```

Use a destination on traversable ground in the same loaded dimension within normal navigation range. The selection searches for a tagged Sable within 32 horizontal blocks and 16 vertical blocks of the executor. `assign_sable` takes a loaded block position, replaces the previous target, and stores the coordinates in the villager's persistent data.

## Manual acceptance
1. Start actual Forge game with installed Hearthbound mod; report build SHA/version.
2. Spawn Sable near player; name is visible and entity tag is present.
3. Run assignment to a reachable destination and record real movement.
4. Cancel mid-route; Sable should stop its assigned journey.
5. Reassign, save and relaunch while the assignment is incomplete; Sable should resume after the chunk is loaded.
6. Assign a blocked/unreachable position; no teleportation and no inventory mutations must occur.
7. Test two users: operator permissions protect assignment and cancellation.
8. Watch server logs for exceptions; record gameplay footage from Minecraft itself.

## Limitations
- Default vanilla villager AI (POI/sleep/panic) can compete with the requested route. A dedicated citizen navigation controller will need explicit job priority.
- This is low-frequency path command refresh, not a path guarantee. Block collision, water, and chunk loading may prevent arrival.
- The assignment does not force-load chunks. During unloading it pauses rather than simulate offline movement.
- No unique persistent colony identity/UUID registry or ownership permissions yet: nearest tagged Sable is used.
- It was committed without a successful ForgeGradle compile/gameplay run. Any API mismatch must be fixed through actual development build.
- No output inventory transfer, Create millstone control, ML inference or genuine gameplay recording has been done.

## Expected future interfaces
`TravelToStation` -> `ReserveStorage` -> `ExtractInputs` -> `Carry` -> `InsertIntoMill` -> `WaitForRealCreateProcessing` -> `ExtractOutput` -> `Deliver`. All inventory changes must be reserved and server-authoritative, with cancellation/restart reconciliation and no duplication.
