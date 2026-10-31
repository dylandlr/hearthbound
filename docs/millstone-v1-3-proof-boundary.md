# Hearthbound v1.3: millstone proof boundary

## Implemented locally
The separately packaged `MillstoneReceiptGate` provides a pure-Java gate for server-side millstone completions. It checks operation UUID, world, dimension, machine coordinate, recipe, and nonempty consumed and produced item stacks. Its 13 standalone Java 17 checks pass.

Artifact: `hearthbound-millstone-receipt-gate-v1.3.zip` (conversation attachment, not automatically installed in this repository).

## Candidate source of completion events
Create Recipe Hooks (https://github.com/Aar0w/Create-Recipe-Hooks) reports server-side Forge `CreateRecipeFinishedEvent` with a `MILLSTONE` source for Create 6.0.8+. Its published contract describes outputs and recipe/machine metadata; `getItemInputs()` is only documented for selected sources and **not millstone**.

Therefore:
- Do not equate this event with verified wheat consumption.
- Do not award research credit until a persistent server-owned transaction state proves actual consumed inputs.
- Bind incoming events to an in-flight UUID for the same world, dimension, position and recipe.
- Distinguish block placer identity from experiment-performing citizen identity.
- Send completed verified evidence to the idempotent journal/reward receiver only once.
- Treat events without a matching operation and input proof as telemetry, not scientific proof.

## Remaining hard blockers
- The v1.1 standalone ledger and v1.3 gate are NOT wired into the current Forge branch.
- Verify event library compatibility and licensing before taking it as a dependency, or instrument the version-pinned Create completion site directly.
- Compile with ForgeGradle; run a real Create millstone GameTest and dedicated-server restart test.
- Show server logs and physical inventory receipts for a legitimate wheat-to-flour run.

No live Minecraft test or Forge compilation is claimed.
