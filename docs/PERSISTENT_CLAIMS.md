# Persistent hauling claims

Hearthbound now proposes a Forge/Minecraft SavedData-backed exclusive source ownership map, scoped per dimension. Claim additions and removals mark SavedData dirty so Minecraft can save them with world state. Existing Sable hauling calls use the same claim/release API.

## Validation
1. Compile Forge sources using CI.
2. Spawn Sable, start a haul, save/stop/restart server, and attempt a competing assignment at the same source.
3. Confirm competing assignment is refused until original delivery or pre-pickup cancellation.
4. Confirm claim release survives a second save/restart.
5. Test stale claims when Sable dies or is removed; **currently manual repair is not provided**.

## Safety caveat
Persisted claims prevent casual competing assignments across graceful restarts but do not establish atomicity with chest, villager, or entity saves. A server crash can still produce inconsistent cargo/inventory counts. Claims can remain stranded after citizen death. This is not an exactly-once transfer protocol and should not be used for valuable resources yet.
