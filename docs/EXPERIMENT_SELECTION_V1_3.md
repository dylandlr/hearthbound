# Hearthbound v1.3 — Experiment selection baseline

Adds a pure-Java `ExperimentSelectionPolicy` for scientific task selection.

**Inputs (observation schema v1):** personal curiosity, locally measured scarcity/fatigue, and a bounded set of candidate experiments. Each candidate contains a proposed recipe, input, nearby machine, expected output, novelty, material cost, actual sensor visibility flags, and previous falsification state. No recipe registry or world search happens inside the policy.

**Outputs:** PROPOSE(candidate) or DEFER. A proposal is not evidence, physical production, research credit, or an unlock. The existing `TechnologyHypothesisSavedData.propose` and trusted Create processing callback remain the authoritative downstream interfaces.

**Deterministic decisions:** utility trades curiosity and novelty against scarce material use and fatigue. Invisible materials/machines, previously falsified conjectures and severe exhaustion are excluded. Ties break by recipe ID for repeatable policy evaluation.

**Tests:** visible candidate preference, unseen-machine and falsification exclusion, resource scarcity/exhaustion, invalid schema and NaN rejection.

**Not yet implemented:** Sensor adapter collecting actual citizen-local candidates from Minecraft/Forge/ Create, hierarchical action executor that proposes and physically attempts the selected experiment, per-agent fatigue model, policy performance benchmarking or trained MLP. All are explicit next gates. This increment is a policy contract, not a claim of in-game autonomous science.
