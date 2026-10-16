# First Mill / Create 6.0.8 integration

Minecraft 1.20.1, Forge 47.4.10, Create 6.0.8 (development artifact 6.0.8-289).

Dependency coordinates and versions follow the official Create developer wiki: https://wiki.createmod.net/developers/depend-on-create/forge-1.20.1

## Verified on source branch

- Existing Sable hauling, restart quarantine, source claims and operator audit preserved.
- Create added as a **mandatory** runtime mod for this branch; no claim of backwards compatibility without Create.
- MillInspector references `AllBlocks.MILLSTONE` and provides server-observed block and item-handler inventory information.
- `/sable mill-inspect <x> <y> <z>` never awards scientific/research credit.
- `scripts/rcon_create_mill_smoke.py` checks block placement, introspection and negative case.
- CI runs actual `gradle compileJava` then `gradle runServer`; this is separate from the existing non-Create smoke workflows.

## Not implemented

No Create millstone rotational power source, completed processing cycle, input/output movement protocol, attributed receipt, recipe proof, observation schema for learning, transfer of knowledge between citizens or deterministic training experiment. Reading an item stack is insufficient evidence of a completed milling recipe. The Create development dependency, mod startup, Create block placement and inspection must pass CI first.

## Next physical First Mill slice

1. Add a controlled Create power fixture (water wheel, shaft and millstone) to disposable dedicated-server test world, or an equivalent demonstrably powered machine fixture.
2. Feed exactly one physically traced wheat with a unique job ID, capture server-recognized processing completion and output changes (without equating an arbitrary flour count with causal proof).
3. Attach processing evidence to citizen experiment logs; only then grant recipe knowledge.
4. Reproduce seeded experiments before introducing neural policies.

Crash consistency of hauling and reconciliation remains a separately tracked limitation. Never claim the first mill is fully demonstrated until a powered machine completes a processing cycle in a real Minecraft world.
