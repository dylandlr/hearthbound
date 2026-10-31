# Hearthbound v1.8 — Read-only millstone diagnostics

Staged on PR #76: operator-only command `/hearthbound millstone inspect <x> <y> <z>`.

It checks that the loaded target block is `create:millstone`, then displays its server dimension, position, Hearthbound SavedData tick, block-entity type and exposed Forge ITEM_HANDLER slots. The command uses server-side block entity state, never a rendered client snapshot.

Limitations:
- An inventory snapshot does NOT prove ingredient consumption, identify the active recipe or establish a recipe completion; some Create internals may not be exposed through ITEM_HANDLER.
- Diagnostic does not attach a citizen UUID or advance research credit.
- No Create Recipe Hooks dependency was added. Before using that library, resolve its distribution/license and verify event API.
- ForgeGradle compile, client startup, server startup, and actual millstone command have NOT been verified. This branch remains a draft.
- The SavedData clock is checkpoint persistent, not crash-proof. UUID journal remains required for reward idempotence.

Manual acceptance:
1. Resolve dependencies and compile: `./gradlew compileJava`.
2. Start a Forge 1.20.1/Create 6.0.8 server with Hearthbound.
3. Use `/hearthbound millstone inspect <x> <y> <z>` on a loaded Create millstone.
4. Record output before placing wheat, during processing, and after output has appeared.
5. Compare captured tick and actual machine state with Create's completion callback. Implement server-owned consumed-input capture at the mutation point before feeding the receipt gate.
6. Validate duplicate replay and restart paths on the actual server before awarding rewards.

This diagnostic is a first physical observation point, not a complete event capture or a gameplay milestone.
