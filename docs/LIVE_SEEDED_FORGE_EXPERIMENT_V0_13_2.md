# Hearthbound v0.13.2 — Execute seeded resource research in actual Forge CI

## Goal

PR #152 validated the intervention-to-observation audit in ordinary CI, but the opt-in `seeded-v1` mode had not run as a completed real Minecraft experiment. This milestone adds **two additional live dedicated Forge server arms** to the existing CI run while keeping both frozen baseline trials.

## Exact CI design

The boot-server matrix contains four explicit jobs:

| Arm | Configured world seed | Resource schedule | Artifact name |
|---|---|---|---|
| SCRIPTED control | `hearthbound-policy-v0-8-10` | `baseline` | `minecraft-policy-trial-SCRIPTED` |
| TRAINED_MLP control | `hearthbound-policy-v0-8-10` | `baseline` | `minecraft-policy-trial-TRAINED_MLP` |
| SCRIPTED seeded research | `hearthbound-resource-probe-A` | `seeded-v1` | `minecraft-policy-trial-SCRIPTED-seeded-A` |
| TRAINED_MLP seeded research | `hearthbound-resource-probe-A` | `seeded-v1` | `minecraft-policy-trial-TRAINED_MLP-seeded-A` |

Each job starts its own disposable Minecraft Forge dedicated server and runs the same established end-to-end acceptance. The seeded arms additionally execute six deterministic, real RCON inventory interventions and archive exact server tick timestamps, the verified mutation schedule, sealed citizen decision/outcome journal, and direct-observation coverage audit. The benchmark remains the **same fixed pair of chest sources**, not naturally generated diverse worlds.

The preexisting comparison job continues to use only the two original baseline artifact filenames. The new `compare-seeded-resource-arms` job separately loads both `*-seeded-A` artifacts and validates their matched seed, identical schedule fingerprint, distinct run IDs, and real-observation coverage evidence. This intentionally does not estimate counterfactual rewards or claim the neural attention policy executed. Both arms may use different legacy task policies while the citizen's attention sampler remains scripted.

## Manual runs

On manually dispatched workflow runs, `world_seed` overrides **only** the seeded research arms. The frozen baseline world and its artifact filenames are unchanged. The seeded schedule remains enabled for those explicit research arms.

## Acceptance criteria

- Both original frozen baseline arms continue to pass Forge startup, perception/social privacy tests, NBT persistence, and existing policy comparisons.
- Both additional seeded research arms must boot a real Forge world and perform the six RCON changes successfully with recorded server ticks.
- Both seeded arms must produce internally valid, finalized Forge attention journals and intervention-observation coverage records.
- The new comparison job must accept only correctly matched seeded-arm provenance and refuse duplicate run IDs, mismatched seed/schedule, forged coverage digest, missing or invented evidence.

## Scientific limits

The seeded and baseline arms run different configured world seeds, but the fixture's geometry and setup are still hard-coded. Even verified distinct seeds are not evidence of ecological diversity or independent learned-agent generalization. The output remains a descriptive controlled sensor-coverage study. No live neural attention action authority is introduced.
