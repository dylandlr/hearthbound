# First Mill: Create discovery gate

The first production chain is **wheat field → Sable logistics → Create millstone → wheat flour → stockpile**. This remains a gameplay milestone; it is not implemented end-to-end.

## Available optional Create commands

- `/hearthbound create_status` reports whether Create is installed and whether `create:millstone` and `create:wheat_flour` exist in Minecraft's actual registries.
- `/hearthbound inspect_mill <x y z>` verifies a loaded block at the given position is a real registered Create millstone.

The bridge uses runtime registry discovery so Hearthbound still starts without Create. **It does not assert rotation, power, processing progress, valid recipes, or flour production.** Those require a subsequent Create-aware integration test.

## Acceptance criteria for a real mill

1. Install a compatible Create mod in Forge 1.20.1 test profile and verify registry discovery.
2. Detect real kinetic power, paused/stalled machine state and processing completion.
3. Deliver four wheat to the millstone input through Sable's real job.
4. Confirm four wheat removed from stock and physically processed into the actual Create recipe outputs.
5. Return produced materials to a colony stockpile without loss/duplication.
6. Repeat through dedicated-server restart and multiplayer client observation.

Do not mark First Mill complete until a Create-installed server integration run actually processes items.
