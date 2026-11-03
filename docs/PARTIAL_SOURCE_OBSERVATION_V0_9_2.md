# v0.9.2 — Partial source observations in real Minecraft

The previous v0.9.1 live trial demonstrated that **both** scripted and MLP arms were rejected when the source chest was empty. Its CI then failed while restoring the fixture: Minecraft returned `Could not set the block` when asked to replace a chest with an identically typed chest differing only in NBT. The fixture is now cleared to air before being rebuilt. This is a harness fix, not a new model capability.

## Read-only wheat-source observation v1

`SourceWheatObservation` reads a real loaded source block's inventory without mutation, task assignment, or chunk loading. For the marked villager Sable within 16 blocks, results are:

- `AVAILABLE`: supported inventory with one or more wheat, including observed count.
- `EMPTY`: supported inventory with zero wheat.
- `UNKNOWN`: chunk unloaded, no block entity, unsupported inventory, villager outside sensor range, or ambiguous marked Sable identity.

Each result contains the Minecraft game tick at observation time. `UNKNOWN` never asserts that a resource is absent. The admin-only command `/hearthbound policy_source <blockpos>` exposes these observations for research, not gameplay authority.

## Real Forge acceptance

Each scripted and MLP trial asserts an empty chest returns `EMPTY wheat=0`, an air block returns `UNKNOWN wheat=0`, and the rebuilt chest with real wheat returns `AVAILABLE wheat=1`. The strict CI artifact parser requires all three receipts, their associated raw Minecraft RCON observations, and stores `source-observations.json`. The prior shortage refusal, real wheat-to-flour task, persisted citizen experiment, reward ledger and comparison remain required.

## Research limitation

This adds an observation **sensor**, not a new neural feature or neural model. The bundled 5→12→4 imitation MLP still cannot infer source availability itself. That separation is intentional until we version an expanded observation schema, explicitly model stale/unknown resource state, generate a genuinely diverse dataset, retrain with held-out tasks and prove runtime feature parity.

A successful trial will establish that we can acquire relevant partial resource information from actual Minecraft without omniscient inventory lookup. It will not prove reinforcement learning, autonomous shortage recovery, or model superiority.
