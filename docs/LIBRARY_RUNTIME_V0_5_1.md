# Colony Library Runtime v0.5.1

## Implemented
Server-side LibraryStudyRuntime and Forge LivingTickEvent subscriber. The vertical slice
accepts a physical container holding `minecraft:written_book`, a selected villager,
a library position, and a literacy score. Study progress is saved in the villager's
persistent NBT and increments only on valid server ticks adjacent to the loaded
container. A missing book, chunk unload, or moved citizen interrupts the session.
At 200 uninterrupted eligible ticks, the citizen receives low-confidence
`READ_BOOK` knowledge for `create:milling/wheat`.

## Important limitations
This is a physical-access runtime component, not the full game interaction.
A command/UI/task planner for starting study is not implemented yet; the caller
must invoke `LibraryStudyRuntime.begin(level, citizen, position, literacy)`.
The written book is only an initial placeholder and the content/title of the
book is not authenticated; any written book presently satisfies the first-slice
requirement. Do not expose this as a general gameplay research mechanic without
content identity, ownership/permission checks, and documented lesson mapping.
This service does not extract Patchouli/Ponder content. It does not grant
practical machine mastery. Integration has not yet been compiled or tested
inside a running Forge/Create Minecraft instance.

## Next integration
Add a scoped /hearthbound library study command for playtesting, then introduce
a dedicated library block/book case and verified mod-book adapters. Hook study
actions into the hierarchical task planner with navigation and interruption
handling. Verify restart/replay safety in a dedicated server test world.
