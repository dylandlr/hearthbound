# Hearthbound v1.5 — Citizen-local experiment site discovery

Adds a bounded survey of physically loaded Minecraft blocks, centered on a citizen. The observer scans within eight blocks horizontally and two vertically, and never loads chunks or reads globally known recipes.

`LocalExperimentDiscovery.nearest` identifies nearby accessible wheat inventories using the existing read-only hauling observer, and genuine registered Create millstones. Candidates are sorted by distance from the citizen with deterministic position tie-breaking. A missing source or millstone yields DEFER rather than a fabricated experiment.

`sable experiment-discover` (operator/admin diagnostic command) passes discovered positions to `LocalMillExperimentSensor` and then the deterministic experiment policy. Only a selected experiment can create a PROPOSED research hypothesis. Existing actual Create receipt validation remains required for confirmation and research credit.

The real-server First Mill smoke has been extended to use `experiment-discover`, without manually providing the machine/source coordinates to the proposal command.

**Remaining gaps:** The diagnostic command is still operator-triggered rather than scheduled in an autonomous citizen tick; it does not physically transport wheat or activate a machine. This is a local observer plus proposal policy, not a complete autonomous scientist. The survey currently knows only the wheat/millstone candidate template and searches a bounded 17x5x17 volume. Forge compilation and dedicated-server execution are the merge gates.
