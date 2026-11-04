# Hearthbound v0.13.8 — Real Forge attention latency audit

## Empirical motivation

[PR #158](https://github.com/dylandlr/hearthbound/pull/158) passed all nine server jobs and its multi-seed comparison. The verified Forge report for configured world seeds **A, B, and C** recorded the following narrow result:

| Configured seed | Scripted witnessed | Neural witnessed | Verified neural-selected source inspections |
|---|---:|---:|---:|
| A | 6 / 6 | 6 / 6 | 13 |
| B | 6 / 6 | 6 / 6 | 14 |
| C | 6 / 6 | 6 / 6 | 14 |

The same geometry and scheduled resource fixture is used in every world, so this does not establish broad generalization, and its observation coverage metric cannot distinguish policies at 100%.

## More sensitive—but still observational—measure

The existing finalized real Forge observation-coverage records include the server tick immediately after each RCON resource mutation and the first subsequent matching **directly observed selected-source** state. Each intervention's first-witness delay is

`first_matching_observation_tick - mutation_tick_after`,

where the recorded first matching tick is strictly after the mutation and strictly before the next same-source change or explicit experiment cutoff. An intervention with no matching direct inspection is **censored**, not assigned a made-up latency.

`scripts/report_matched_attention_latency.py` independently checks each source report's exact schema and SHA-256, event order, interval boundaries, total witness accounting, matching seed and intervention digest, and exact source-and-target-wheat intervention identity. It outputs per-event descriptive delays, observed-only mean and median delays, counts of direct selected-source inspections within each interval, contradictory selected observations, and a descriptive neural-minus-scripted difference when both arms witnessed the event.

`scripts/report_attention_latency_cohort.py` aggregates at the **configured-seed-pair** level, requiring at least three unique seed pairs and six distinct finalized runs. All summaries explicitly deny causal effects, identical intervention tick timing, statistical significance, independent world diversity, and online Minecraft neural learning. Mean latency among witnessed events is *not* a full time-to-detection estimate if one selector fails to witness some events.

## CI

The nine-server Forge job remains as before. Its `compare-multi-seed-live-attention` job now downloads the six existing real A/B/C scripted/neural trial artifacts, audits their per-intervention timing, and archives `latency-seed-A.json`, `latency-seed-B.json`, `latency-seed-C.json` and `forge-attention-latency-cohort.json`. Dedicated regression tests reject forged first-observation ticks, mismatched resources, duplicate runs and unsupported causal claims.

## Next actual environment challenge

Once timing metrics pass on real server artifacts, introduce a separate **fast-resource schedule** where changes can occur faster than the existing five-tick sampling budget, then a **four-source contention** fixture. Preserve the frozen two-source suite as the exact baseline and never change its historical report values. Record change schedules and all operator interventions with authoritative tick timestamps. Evaluate observation coverage and time-to-detection separately, rather than inferring unseen resource states from an on-policy journal.

No LLMs or uncontrolled colony task authority are introduced.
