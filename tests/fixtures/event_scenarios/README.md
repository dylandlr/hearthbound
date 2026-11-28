# Scenario-v1 fixed oracles

`basic.config` is a canonical two-scope, two-rule input. `golden-index.tsv` has seven fields:
seed, mode, trial ID, manifest filename, manifest SHA-256, scheduler-v2 schedule SHA-256, and
derived journal run ID. Nine frozen manifests cover seeds 0, 7, and 9223372036854775807 crossed
with treatment, sham, and no_event. `latent-choices.tsv` separately pins seed, rule ID, ordinal,
scope ID, onset, duration, intended ppm, and the selected positions.

The expected bytes were constructed once using an independent fixture calculation with explicit
scope fragments and rule values plus Python's `hashlib` and `struct` primitives. That calculation
did not import either production implementation. These files are static test inputs: tests never
regenerate them from the code under test. Oracle changes require review against
[the scenario-v1 byte and draw specification](../../../docs/C14_SEEDED_SCENARIO_CONTRACT.md).

Example pinned choices for seed 0: crop slot 0 selects field-a, onset 12, duration 2, intended
165598 ppm, targets (0,64,0) and (1,64,1); crop slot 1 selects field-b, onset 15, duration 7,
intended 812625 ppm, targets (10,64,0) and (12,64,0). These are synthetic plan oracles, not
observations of a Minecraft world or successful physical disruptions.
