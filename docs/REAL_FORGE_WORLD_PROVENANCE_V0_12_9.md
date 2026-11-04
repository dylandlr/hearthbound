# Hearthbound v0.12.9 — World-seed and fixture provenance

The existing Forge smoke workflow generates separate finalized experiment run IDs for SCRIPTED and TRAINED_MLP trials, but has historically configured **the same Minecraft world seed and fixed two-chest fixture** in both arms. This milestone makes that limitation machine-readable rather than treating separate run IDs as independent trials.

## Captured per-arm metadata

Before the Forge server starts, `capture_real_forge_world_provenance.py` reads the exact CI `run/server.properties` file and verifies the expected configured seed, world name, offline-mode/RCON configuration, policy arm, and test fixture identifier. It records a SHA-256 of the configuration file in `real-world-provenance.json`. No private RCON password is copied to the JSON output. This captures **configured properties**, not an independent in-game check of generated terrain.

## Cohort interpretation

The compare-policy-arms CI job collects the SCRIPTED and TRAINED_MLP metadata and runs `validate_real_forge_run_cohort.py`. The output `real-forge-cohort-provenance.json` reports the number of distinct configured seeds, fixture IDs, and whether the runs are same-seed matched controls. It always sets `independent_world_conditions_verified=false` and `generalization_claim_allowed=false`. Even different configured seeds are not proof that the fixture yields different meaningful learning opportunities.

## Safety and validation

Unit contracts reject missing/duplicate server properties, incorrect expected seed, invalid policy identities, duplicate cohort entries, and false independence claims. The RCON acceptance still uses exactly the existing test world and does not enable neural attention execution. This milestone is provenance instrumentation, not a multi-seed behavioral success claim.

## Subsequent experiment

Add an explicit opt-in multi-seed dedicated-server research workflow with fresh world directories, reproducible source-change schedules, verified fixture identifiers and grouped run-level evaluation. Separate full-world train, validation, and test splits, then evaluate the impact of world/fixture diversity. Never treat individual decisions within one run as independent samples.

## Manual reproducible world-seed runs

The dedicated-server smoke workflow now exposes `workflow_dispatch.world_seed`. The default is the frozen historic `hearthbound-policy-v0-8-10` seed. A manual run can supply another configured world seed; both SCRIPTED and TRAINED_MLP acceptance arms receive the same selected seed, preserving within-seed comparability. The seed is written into disposable server.properties, checked against the recorded provenance, and archived per policy. Automatic PR checks keep the unchanged default.

Example experimental cohort design (not yet completed): dispatch three separate runs using `hearthbound-provenance-A`, `hearthbound-provenance-B`, and `hearthbound-provenance-C`. Download the verified experiment artifacts for each, validate their run IDs and provenance, and only then consider grouped analysis. Identical hard-coded source-chest fixtures across seeds still limit environmental diversity. Do not report these as independent-world **learning results** without stronger world-condition variation and valid held-out evaluation.
