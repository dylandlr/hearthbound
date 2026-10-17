# Library research integrity v0.6.5

## Change
A random written book no longer counts as a Create milling manual. The study
executor checks a physically present written book with a server-checked
`hearthbound.lesson = hearthbound:basic_milling` NBT marker. The autonomous
container scan delegates to the same eligibility function, so discovery and
execution cannot disagree about what counts as an eligible book.

## Test workflow
1. Use `/hearthbound library primer` with operator permission to receive
   a development milling primer.
2. Put this primer in a chest or barrel. Place a villager within eight blocks.
3. Run `/hearthbound library priority 1` and
   `/hearthbound library auto on`.
4. Inspect with `/hearthbound library inspect` after enough server ticks.
5. Repeat with an ordinary written book. No learning should occur.
6. Repeat after removing the marked book mid-study, with study priority zero,
   and with an active hauling task.

## Limitations
An operator-issued NBT marker is a test fixture, not cryptographic
authentication. Real mod books need a trusted content registry, lesson
metadata and access-policy checks. The single candidate study policy still
does not arbitrate all work types. The Forge build and Minecraft E2E tests
remain unverified.
