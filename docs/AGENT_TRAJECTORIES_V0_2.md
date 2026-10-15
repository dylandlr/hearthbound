# Agent trajectories v0.2

The trajectory layer records the same policy boundary used by the fast simulator and the Minecraft adapter. Each JSONL row contains:

- schema and observation-schema versions;
- episode and step identity;
- the fixed 20-feature pre-action observation;
- the authoritative action mask and chosen hierarchical task;
- whether server-side validation accepted the task;
- named personal and colony reward components;
- a deterministic post-state fingerprint;
- terminal status.

`TrajectoryDatasetV02.generate` produces reproducible scripted-baseline episodes. Tree, random-forest, and MLP trainers should consume this format rather than reading simulator internals.

`MinecraftMillObservationAdapter` is read-only. It maps existing First Mill work-order NBT, haul cargo, loaded barrel inventories, and real Create millstone item handlers into `MillObservation`. Unloaded or unavailable stations remain hidden instead of being interpreted as empty.

The adapter does not execute policy actions yet. The next boundary is a server-side executor that revalidates the observation world version and action mask before assigning an existing hauling operation.
