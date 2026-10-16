# First Mill v5.7 — real dropped-item ingress negative control

## Baseline
The v5.6 Sable gameplay workflow passed at `7b2949d1`. Its tests cover Sable's authorized wheat delivery, the Forge item-handler and Create direct-belt negative controls, and successful direct-belt insertion into an unreserved millstone. The full four-workflow status of v5.6 must be checked separately.

## Physical Minecraft regression added
The end-to-end RCON test now uses an actual Minecraft `item` entity with one wheat, summoned above the **powered, reserved** first research mill:
- Uses the same dropped-item route as the standalone powered Create wheat-to-flour test.
- Confirms the reserved mill's observed wheat count remains zero over several checks.
- Confirms the tagged item entity still exists near the mill and then cleans up only the tagged fixture item.
- Runs the existing direct-belt and Forge item-handler negative controls and the Sable-delivery/recipe-receipt checks.

## Interpretation
This is a real server-world item-entity ingress test, not a motorized belt assembly; the fixture avoids falsely claiming an animated conveyor line was built. The isolated unreserved Create powered-milling test already proves that **dropped wheat can normally be processed**. In combination these are stronger negative and positive controls for access enforcement.

The scope remains guarded research-mill access through the currently instrumented routes, not a general security boundary against direct inputInv edits, arbitrary NBT edits or one-for-one identical item substitution. Do not award technological discovery or agent XP. Latest CI must confirm this new regression before marking it verified.
