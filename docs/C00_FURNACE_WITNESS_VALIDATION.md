# Independent native furnace witness validation

Parent: [C00-02 / #227](https://github.com/dylandlr/hearthbound/issues/227).
Change: [draft PR #275](https://github.com/dylandlr/hearthbound/pull/275), published source
`8206ca0e3bb6668e896ecb03d7bd1b0269ae7f50`.

**The strengthened furnace gate passed four fresh native trials and their clean restart checks.**
The separate broad smoke matrix has failures with an unresolved arrival diagnosis, so this is not an all-CI-green
or integration-acceptance claim.

## Why the check changed

The [historical v0.23 audit](C00_BASELINE_ARTIFACT_AUDIT.md) found that the physical validator
accumulated furnace recipe counts from event records but never compared the independently captured
native `RecipesUsed` responses. An internally consistent event history could therefore pass despite
a missing or conflicting world witness.

The correction parses complete native responses for the two configured furnaces, requires zero
initial counters in this fresh fixture, and reconciles final counters against verified bake events
for each furnace separately. Missing, duplicated, malformed, foreign or inconsistent responses fail
the gate. Swapped per-furnace counts cannot pass merely because their sum is unchanged.

The parser is deliberately restricted to the actual English Minecraft 1.20.1 response subset and
this pinned fixture. It is not a general SNBT parser or an acceptance path for pre-existing furnaces.
This is an engineering correction; it introduces no new AI research result.

## Verification

- All 14 focused regression tests passed, including otherwise consistent histories with only the
  independent witness changed or removed.
- All four historical v0.23 payloads passed the stronger validator with unchanged physical audits.
- Fresh [native cohort run 46090831818](https://github.com/dylandlr/hearthbound/actions/runs/46090831818)
  succeeded at the exact published head. All four payloads identify `REAL_FORGE_CREATE`,
  `passed_live_and_restart`, and the expected source SHA.
- All five downloaded artifact ZIPs matched GitHub's SHA-256 digest and byte size. The strict
  validator was rerun independently against the four fresh payloads, reproducing their stored
  physical audits and the cohort summary.

All eight initial furnace counters were zero. Counter order below is `(36,101,5)` followed by
`(36,101,27)`. Each final counter independently matches that furnace's recorded bake events.

| Seed | Arm | Final native counters | Bread after drain | Meals after drain | Productive completions | Failed / all settled jobs |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 23001 | adaptive | 10 / 10 | 20 | 14 | 131 | 253 / 521 |
| 23001 | authored | 8 / 11 | 19 | 14 | 115 | 346 / 579 |
| 23002 | adaptive | 5 / 12 | 17 | 12 | 115 | 262 / 544 |
| 23002 | authored | 11 / 11 | 22 | 15 | 128 | 286 / 527 |

The functional cohort gates passed in each slot. Failed work remains in every denominator.
Horizon observations occurred at 7200–7203 ticks; the table reports separate post-drain totals.
At the measured horizon, adaptive-minus-authored bread differences were +1 and -4; meal differences
were -1 and +1. These are descriptive results from two seed pairs, not evidence of causal benefit.

[The machine-readable verification](evidence/civilization100/furnace-witness-native-validation.json)
records run and artifact identities, ZIP sizes and digests, validator hash, payload hashes, native
counters, horizon and terminal results, and evidence limits. The original historical audit remains
separate and unchanged.

## Limits and open integration gate

These are eight-citizen authored fixtures with known capabilities, supplied machines and accelerated
crop random ticks. Their controller is not neural, and no deep-MARL, 100-citizen, persistent occupation,
or causal learning/communication claim is made. Restarts were clean after work drained; abrupt-crash
atomicity is untested. This review downloaded and replayed the CI evidence rather than launching
another local server, and did not repeat the historical policy-history forensics.

The independent [dedicated-server smoke matrix](https://github.com/dylandlr/hearthbound/actions/runs/46090831824)
reported three failures. One SCRIPTED-baseline job failed during Gradle `:downloadAssets` on a horse
sound before Forge readiness; the logs do not distinguish transport from asset validation failure.
The TRAINED_MLP baseline and SCRIPTED resource-probe-A jobs booted Forge and verified source wheat
8→7 and destination wheat 0→1, then failed a subsequent 2.6-block citizen-proximity query. Their logs
lack both delivery-time and failed-query position data. Movement after valid delivery, timing,
geometry differences and an arrival/execution defect remain distinguishable hypotheses, not findings.

The smoke workflow, smoke and haul-diagnostic scripts, SableHauling and SableController are
byte-identical to the successful scheduler comparison head. The furnace validator is not imported or
called by this path. This narrows attribution but does not dismiss the failed physical-arrival checks.
The smoke jobs used a synthetic merge whose Git tree equals the published correction tree.

At the diagnosis snapshot, the matrix had seven successful, three failed and one running boot jobs.
The [retained diagnosis](evidence/civilization100/furnace-witness-smoke-diagnosis.json) identifies the
cases, exact sources, excerpts, pending outcome and comparison evidence. Check the linked run for
later status. [QA issue #348](https://github.com/dylandlr/hearthbound/issues/348) requires the missing
evidence, a bounded reproduction, and a justified repair while preserving material and physical-arrival
criteria. No workflow was rerun to replace the failures, and no root-cause fix is claimed.

Draft PR #275 and C00-02 stay open pending the applicable review and integration gates.
