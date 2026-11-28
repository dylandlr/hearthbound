# C00-02: audit of the historical v0.23 native artifacts

Audited on 27 November 2026 (user date). Parent ticket: [#227](https://github.com/dylandlr/hearthbound/issues/227).

**The artifact-content audit passed. The integrated-baseline ticket remains open.**
This report reviews historical evidence; it does not select an integration base, merge a branch,
run a new server, or establish a new colony capability.

## Source and reproducibility

The candidate is `feat/renewable-village-economy-v0-23` at
`a072519518db1458e8cb5aa1898aebd4ba93f03a`. The source is
[Renewable village economy run 45511112716](https://github.com/dylandlr/hearthbound/actions/runs/45511112716),
run attempt 1, with two configured seeds and adaptive/authored conditions.

All five ZIPs were downloaded, read, and verified against GitHub's artifact digests. All four
planned slots are present. Each acceptance JSON reports `passed_live_and_restart`,
`origin: REAL_FORGE_CREATE`, and the expected commit. The four complete event histories were
replayed with the unchanged historical policy and material validators. Their recomputed outputs
match the per-world acceptance files and cohort summary.

| Artifact | Verified ZIP SHA-256 |
| --- | --- |
| [village-23001-adaptive](https://github.com/dylandlr/hearthbound/actions/runs/45511112716/artifacts/14979255004) | `5dd6e89b8e7bedee50bb737685b36289fcd2f909524e1b5a2a82c77d98889077` |
| [village-23001-authored](https://github.com/dylandlr/hearthbound/actions/runs/45511112716/artifacts/14978101744) | `7db97766ad004061e1479482cbb50941cbbb8270b71f8703359254c97600991d` |
| [village-23002-authored](https://github.com/dylandlr/hearthbound/actions/runs/45511112716/artifacts/14977940753) | `8cca7f5a864cb6424a9cb72f9b33857aa82b6b0485307d92d55104dd9695fbff` |
| [village-cohort-summary](https://github.com/dylandlr/hearthbound/actions/runs/45511112716/artifacts/14977837333) | `885dbfd47cb7f08275d9fe9a32036c4aaca371652dde8c0351b0c5b10bea8985` |
| [village-23002-adaptive](https://github.com/dylandlr/hearthbound/actions/runs/45511112716/artifacts/14977602889) | `a564fad3c57d6d639113c9f0b7996aeb3f0363fc460cd180f7e5f4dfba9cf30a` |

Machine-readable audit inputs, results and the stronger validator replay are retained under
[docs/evidence/civilization100](evidence/civilization100/). These are derived audit records, not
substitutes for the original ZIPs. Original CI artifact retention is finite; the links are provenance,
not a guarantee of permanent upstream availability.

## What the archived trials establish

| Seed | Arm | Event records | Decisions replayed | Horizon bread / meals | Final bread / meals after drain | Failed settled jobs |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 23001 | adaptive | 9,102 | 544 | 17 / 12 | 19 / 13 | 256 |
| 23001 | authored | 8,950 | 563 | 20 / 12 | 21 / 15 | 334 |
| 23002 | adaptive | 8,793 | 490 | 20 / 10 | 21 / 14 | 209 |
| 23002 | authored | 8,802 | 546 | 20 / 10 | 21 / 15 | 310 |

Every slot contains eight surviving, productive, multi-capability citizens. Their archived native
entity responses report health 20. Native regrowth and reharvest occurred on 6, 7, 6 and 5 plots,
respectively. Demand returned at approximately tick 4200, followed by 59, 51, 60 and 59 jobs.
All failures remain in the recorded histories and private-learning replay; most were resource
reservation conflicts. A passed cohort gate does not mean every action succeeded.

Native inventories, furnace recipe responses, policy totals, eight private learner digests per
world, and cleared custody agree across the drained clean restart. The 19, 15, 20 and 18 native
Create callbacks agree with their event identities, conversions and processing times. Build and
server logs contain the expected success/startup markers and no lines matching the checked
`ERROR`, `Exception in thread`, or `Caused by:` patterns. This is a scoped log check, not proof that
all possible warning or failure conditions are absent.

## Comparison and limits

At the measured horizon, adaptive minus authored meals are **0 for both seeds**; the corresponding
bread differences are **-3 and 0**. These are descriptive observations from two seed pairs, not
statistical evidence of a learning advantage. Four distinct world UUIDs were used. Equal world seeds
do not freeze citizen UUIDs, loot randomness, execution order, or all other sources of variation.

Horizon observations occurred at 7201–7203 ticks. The final totals include a later drain and must
not be substituted into the horizon comparison. The restart was clean after work drained; abrupt-crash
atomicity was not tested here.

All four acceptance payloads explicitly record `neural_controller: false`,
`causal_learning_advantage_claimed: false`, and `causal_communication_benefit_claimed: false`.
The private execution-cost learner is RLS. The world is an authored eight-citizen fixture with known
skills, utilities, recipes, machines and accelerated crop random ticks. These results do not establish
deep MARL, a 100-citizen population, autonomous construction, recipe discovery, or durable occupational
specialization. Eight citizens performing several capabilities is not a specialization milestone pass.

## Concrete acceptance gap and correction

The original `validate_physical()` accumulated furnace recipe counters from event fields but did not
compare the separately captured native `after.furnace_recipes` responses. That could admit an internally
consistent event ledger even when the independent native witness disagreed.

A separate comparison of those native responses matched all four historical runs. For furnaces
`(36,101,5)` and `(36,101,27)`, the respective counts are 7/12, 8/13, 9/12 and 10/11. The historical
archives are therefore not contradicted; the problem was an executable-gate coverage gap.

[PR #275](https://github.com/dylandlr/hearthbound/pull/275) adds the missing independent comparison,
strict response and identity validation, and negative tests that change only the native witness while
keeping the material history consistent. All 14 focused tests and all four archived replay payloads
pass locally. Current native CI evidence belongs to that PR and must be checked at its published head.

This parser and reconciliation correction is ordinary engineering validation. It does not add a
research-performance claim or grant new capabilities to citizens.

## Remaining C00-02 gates

- Reconcile the candidate's ancestry with remaining active PRs and competing heads.
- Review the capability matrix and select the integration base.
- Record the rollback reference and integration decision.
- Integrate the focused furnace-witness correction only through its own review and CI gates.

The artifact-content inspection item in #227 is complete. The broader ticket stays open; no
unverified feature should become Done because this audit passed.
