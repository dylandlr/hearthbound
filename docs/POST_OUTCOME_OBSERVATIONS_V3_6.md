# Hearthbound v3.6 — Observed or unavailable successor samples

After MillResearchRewards produces a physically verified award, ResearchTrainingRuntime samples the citizen's nearby eligible physical experiment context using LocalExperimentDiscovery and LocalMillExperimentSensor. The result is encoded into an 11-feature ResearchObservationVector, but **only if the sensor can genuinely provide a valid observation**.

If the experiment has become ineligible (e.g. already known recipe), the source/machine is missing, or physical visibility fails, the system records UNAVAILABLE with null features. It does not fabricate a zero state or treat observation absence as a terminal episode. The result is saved by verified job/citizen UUID in ResearchSuccessorObservationsSavedData.

## Guarantees
- Post-award citizen and machine IDs are checked against the verified award.
- OBSERVED and UNAVAILABLE are explicit, immutable alternatives with versioned SavedData serialization.
- Stored samples reject conflicts for the same job.
- Original research rewards and physical evidence remain authoritative; diagnostics do not award or teach.

## Limits
- The current sensor is an *experiment eligibility* sensor, not a generic post-research world-state sensor. After discovery, it commonly returns null; UNAVAILABLE is expected. A separate locally grounded general-purpose sensor is needed for broader successor coverage.
- This is not yet a complete (s,a,r,s',done) generator, nor is an MLP trained.
- Feature vectors and reward journals remain separate SavedData objects with non-atomic save boundaries. Requires crash tests and coherent sample assembly.
- Runtime hook and NBT round-trip tests are authored, but Forge compile, real client/server execution, and post-restart acceptance checks remain unverified.

## Next milestone
Build an always-available (when citizen and chunk loaded) local status sensor independent of research eligibility, with explicit masks for unavailable fields, then atomically specify export and verify full transitions in a real Minecraft scenario.
