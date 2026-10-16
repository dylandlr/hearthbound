# First Mill v5.6 — reserved versus unreserved belt controls

## Known baseline
The most recently verified four-workflow Minecraft baseline is `123b8633` (Forge insertion guard). The v5.5 Create direct-belt Mixin runs are still pending at the time of this change; do not claim v5.5 passed until CI confirms it.

## New control
The actual Create direct-belt entry method must behave differently depending on Hearthbound research-machine state:
- **Unreserved millstone**: `/sable mill-probe-open-belt x y z` inserts one wheat via Create's `DirectBeltInputBehaviour.handleInsertion`; the command reports `OPEN_BELT ACCEPTED` only if the insertion remainder is empty.
- **Reserved millstone**: `/sable mill-probe-belt-insert x y z` performs the same insertion route without a Hearthbound authorization scope; the command must report `BELT_INSERT DENIED`, preserving the input.
- The gameplay RCON regression checks the unreserved machine's inspector reports `wheat=1` and the reserved machine's inspector reports `wheat=0` after both attempts.

These are behaviour-level server-side tests, not a complete motorized conveyor assembly simulation. Full physical belt transportation, funnel behavior, multiplayer item pickup, direct raw `inputInv` edits and other capability routes remain outstanding. No research unlocks or rewards.
