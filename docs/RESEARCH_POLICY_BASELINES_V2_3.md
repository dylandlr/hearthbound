# Hearthbound v2.3 — Research policy baselines

A new pure Java `ResearchPolicyBaselines` interface accepts the same versioned partial-observation contract for two deterministic modes: `SCRIPTED` (fixed curiosity=0.60) and `PERSONALITY` (per-citizen exploration instinct). Both preserve scarcity, fatigue, visibility, costs and falsification gates and use the identical experiment selection algorithm. They differ only in personality conditioning.

`LocalMillExperimentSensor.consider(..., mode)` wires both modes to the live-world sensor, retaining the original four-argument entry point as the current personality default. JUnit verifies script reproducibility regardless of citizen curiosity, personality-sensitive outcomes, and no invisible-material override.

**Limitations:** There is not yet an in-game mode-selection command or a controlled per-seed A/B run. This is a policy comparison seam and test baseline, not evidence of trained AI or measured superiority. The existing autonomous scheduler continues to call the default personality mode. Next task: persist a policy assignment on citizen NBT, expose operator mode selection and record it with the benchmark, then run paired seeds. LLMs remain deferred.
