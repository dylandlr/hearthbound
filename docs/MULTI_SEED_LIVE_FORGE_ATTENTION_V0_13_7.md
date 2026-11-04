# Hearthbound v0.13.7 — Multi-seed live Forge attention cohort

This milestone follows #157. The first real matched script-versus-neural Forge experiment recorded **6 of 6 matching directly observed resource interventions** in each policy arm, with **13 verified neural-selected inspections** in the measurement window. This is authentic Forge source-choice evidence, but it saturates the six-event observation-coverage measure; it does not show a neural advantage.

## Controlled additional worlds

Extend the dedicated Forge server CI matrix from 5 to 9 arms:

| Configured seed | Scripted attention arm | Neural attention arm |
|---|---|---|
| hearthbound-resource-probe-A | Existing scripted control | Existing neural intervention |
| hearthbound-resource-probe-B | New scripted control | New neural intervention |
| hearthbound-resource-probe-C | New scripted control | New neural intervention |

The two historic policy-trial baseline arms and the separate scripted TRAINED_MLP-labeled seeded-A arm remain unchanged. Neural is enabled by operator command only during the seeded intervention window, then disabled before cleanup. All source decisions and results are recorded by the real Forge attention journal; source reward on unselected actions is never guessed.

Seeds B and C produce distinct deterministic SHA-256 resource-intervention schedules and are written into server.properties. **All nine servers still use the same hand-built chest geometry and source-registration logic.** A different configured seed alone does not prove terrain diversity or broad generalization.

## Experiment evaluation

`scripts/report_matched_live_attention.py` validates each A/B/C scripted/neural pair's actual verified coverage, common seed, resource-schedule digest and distinct finalized run IDs.

`scripts/report_multi_seed_live_attention.py` then requires **at least three** nonduplicated configured-seed pairs, valid report hashes, unique underlying run IDs, and internally consistent six-intervention witness counts. It reports the unweighted mean and range of per-pair descriptive coverage differences. Its primary unit is the **matched configured-seed pair**, never an individual inspection event. It explicitly sets false for independent world-condition verification, naturalistic source dynamics, statistical significance, causal treatment attribution, online Minecraft neural learning, and broad generalization claims.

CI archives all per-seed pair comparisons and a multi-seed cohort summary.

## Acceptance

- All original server acceptance tests still pass, including the baseline Forge journals, restart persistence, personal-memory privacy and seed-provenance validation.
- Each new B/C neural arm verifies at least one actual neural-selected source inspection **during** the controlled six-intervention measurement interval.
- Each new B/C scripted arm remains on the original least-recently-sampled selector.
- Each cross-arm comparison has the same configured seed, intervention digest, and distinct finalized run IDs.
- Multi-seed reporting refuses duplicate seeds, invalid self-hashes, inconsistent observation counts, or claims that these tests measured a randomized treatment effect.
- Do not publish experimental results from seeds B/C until their real Forge CI and comparison artifacts finish successfully.

## Limitation and next research priority

The current source changes are slow enough that both attention strategies may achieve perfect 6/6 witness coverage. Repeated ceiling performance would establish **reproducibility of this narrow acceptance task only**. A stronger experiment must introduce faster and less predictable resource-change regimes, 3–4 watched resources, variable resource accessibility and controlled sensor outages with real tick-based stimuli, while preserving one inspection per five ticks and holding out entire world/fixture configurations. A successful narrow experiment does not yet demonstrate emergent colony intelligence.
