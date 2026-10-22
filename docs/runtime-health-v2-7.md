# Runtime verification v2.7

`/hearthbound status` reports:
- Hearthbound bootstrap command registered
- whether the authoritative Forge `ModList` contains `create`
- Hearthbound's saved logical tick
- current server dimension
- explicit `researchBridge=not-connected` marker (no simulated success)

The command returns 0 when Create is absent and 1 when loaded. This establishes a basic runtime health check; it does not prove physical milling or agent intelligence.

## First manual smoke sequence
1. Read/accept the Minecraft EULA if you choose to run a server.
2. Use the development server or install the CI JAR alongside compatible Forge and Create dependencies.
3. Run `/hearthbound status` in an operator console/player context.
4. Confirm `Create=loaded` and observe `logicalTick` advancing between two calls.
5. Place a Create millstone and use `/hearthbound millstone inspect <x> <y> <z>`.
6. Record the resulting dimensions, position, inventory slots and ticks with the server log; absence of input stacks in capability does not mean there was no processing.
7. Restart after saving, repeat `/hearthbound status`, confirm the tick counter advances from the stored checkpoint.
8. Do not award any research reward based on this command. Transaction input and output mutations still need trusted hooks and persistent evidence integration.

## Status
JAR build was green on run 39837610832, preceding this status command change. v2.7 status command requires a fresh CI compilation and in-game execution before runtime claims.
