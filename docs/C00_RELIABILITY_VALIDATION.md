# Reliability evidence correction: native validation

Recorded 27 November 2026 (America/Chicago). Related:
[QA #350](https://github.com/dylandlr/hearthbound/issues/350),
[C00-02 / #227](https://github.com/dylandlr/hearthbound/issues/227), and
[draft PR #351](https://github.com/dylandlr/hearthbound/pull/351).

**The corrected evidence pipeline passed its unchanged five-world native cohort, and independent
artifact replay reproduced the acceptance result.** Other CI workflows remain separate; the broad
smoke run finished with seven successes, four failures and five skipped comparison jobs. Its failures
comprise three post-transfer proximity assertions tracked by QA348 and one startup-readiness timeout
linked to the QA354 investigation.

## Why this change was selected

The bounded review of PR210 found that its principal communication and reliability intent was already
represented by the current structured communication journal and separate five-world pipeline.
The legacy regex parser and three-world workflow were not copied. The
[17-path disposition](https://github.com/dylandlr/hearthbound/blob/e74ff781249b50a28f08fc1f589aebf5d064c90d/docs/C00_PR210_SEMANTIC_RECONCILIATION.md)
records the comparison, source identities and remaining frozen-policy evidence boundary.

The justified correction prevents malformed fields from crashing the summary before its denominator
is written, rejects duplicate JSON keys and conflicting duplicates, retains loader-owned source
locators, and checks every plan/result against trusted current source, protocol, workflow run and
attempt. Descriptive `all_trials_passed` stays separate from `acceptance_passed`. Acceptance requires
all existing outcome, prospective-declaration and required-diagnostic gates. Missing trusted context
permits descriptive analysis but cannot certify acceptance.

Seeds, citizen policies, physical operations and scored outcome definitions are unchanged. Fifty-four
focused unit/CLI tests passed, with existing diagnostic/communication/exporter regressions retained.
Independent review exercised 253 synthetic malformed-input cases separately from the test totals.
Those cases are not native worlds.

## Exact source and execution

| Identity | Value |
| --- | --- |
| Published head | `e74ff781249b50a28f08fc1f589aebf5d064c90d` |
| Reviewed/published tree | `ecf8945b895689324aa92df5ba2a1be2fedd4116` |
| Base | `a072519518db1458e8cb5aa1898aebd4ba93f03a` |
| Native run / attempt | [46096305086](https://github.com/dylandlr/hearthbound/actions/runs/46096305086) / 1 |
| Protocol SHA-256 | `b3730f79bbfb643c6704779302a36496a693f8494b7720931913b355ac855fc3` |
| Aggregate job | [140832999587](https://github.com/dylandlr/hearthbound/actions/runs/46096305086/job/140832999587) |

All five world job logs and the summary job confirm checkout of the published head. The separate
[Forge compile job](https://github.com/dylandlr/hearthbound/actions/runs/46096305121) used Java 17
and compiled the synthetic merge `c8361a205b38cfc6fb1262a83ba900b48561c402`, whose complete tree
equals the reviewed tree. The five native preflights also compiled with Java 17, using one build
attempt each. Retained actual patch builds are 17.0.21.1+2 for worlds 01–03 and 17.0.21+9 for 04–05;
the evidence does not represent them as identical environments.

## All five native worlds retained

| Trial / seed | World artifact | Persistent world UUID | Physical / required diagnostic result |
| --- | --- | --- | --- |
| world-01 / 43101 | [15244112051](https://github.com/dylandlr/hearthbound/actions/runs/46096305086/artifacts/15244112051) | `5c418e5e-aa65-4cbd-b8cd-4759b66515b5` | PASS / VERIFIED_COMPLETE |
| world-02 / 43102 | [15242749102](https://github.com/dylandlr/hearthbound/actions/runs/46096305086/artifacts/15242749102) | `911c16ca-a896-4318-a2f2-34027620e45d` | PASS / VERIFIED_COMPLETE |
| world-03 / 43103 | [15243871488](https://github.com/dylandlr/hearthbound/actions/runs/46096305086/artifacts/15243871488) | `4c2029fb-056c-412f-9e6b-1820032903db` | PASS / VERIFIED_COMPLETE |
| world-04 / 43104 | [15243882028](https://github.com/dylandlr/hearthbound/actions/runs/46096305086/artifacts/15243882028) | `b54637b2-9a9f-48f1-9d51-b8b7d12d1a84` | PASS / VERIFIED_COMPLETE |
| world-05 / 43105 | [15243927493](https://github.com/dylandlr/hearthbound/actions/runs/46096305086/artifacts/15243927493) | `1c7cdb5b-22cf-40fe-b15a-d2c14acbf5b6` | PASS / VERIFIED_COMPLETE |

Each archived terminal result records four physically completed transfers, exactly four wheat at the
destination, all four sources empty, zero outstanding claims, and four completed citizens in both
task-audit reads. The saved native NBT independently confirms each actual seed and distinct world UUID.
These are five world units, not twenty independent citizen replicates.

The five world ZIPs and the
[summary ZIP 15243639563](https://github.com/dylandlr/hearthbound/actions/runs/46096305086/artifacts/15243639563)
were downloaded and checked against GitHub byte lengths and SHA-256 digests. Internal source/build,
plan, result, diagnostic, native-save and raw-log identities were inspected. The summary ZIP is
3,058 bytes with SHA-256 `fdf93577d4ca492e2b173e27b511ae326648649f24d827955811634c1884f644`.
The [verification record](evidence/civilization100/reliability-native-verification.json) preserves
all six archive digests, member hashes, actual checkouts, replay commands and per-world audits.

## Replay and denominator behavior

Trusted replay supplied the expected commit, run ID, attempt and the original required-plan and
required-diagnostic switches. It exited zero with **PASS:5, unknown:0, verified plans:5, verified
diagnostics:5, acceptance_passed:true**. All scoring and provenance fields match the CI summary.
The only raw difference is the loader-owned path/index map: GitHub extracts by artifact name and
the local verification extracts by artifact ID. After normalizing that directory naming difference,
the mappings agree. Filenames do not determine trial identity or outcomes.

Interim replay retained missing slots instead of shrinking the cohort:

| Available valid worlds | Planned denominator | Missing/unknown worlds | Acceptance |
| ---: | ---: | ---: | --- |
| 1 | 5 | 4 | False |
| 2 | 5 | 3 | False |
| 4 | 5 | 1 | False |
| 5 | 5 | 0 | True |

The original three-of-four accounting event and the separately defined physical-delivery accounting
event were each observed in 0 of 5 assessable worlds. This small fixed-seed pilot does not establish
general reliability or resolve every historical accounting failure.

World-04 retains a post-window diagnostic pattern: one citizen had unchanged entity tick count while
40 world ticks elapsed across three samples, with loaded/non-ticking sequence flags. The observation
is retained; its cause is not established, and the original physical score is not recomputed from
that later pattern. Complete required diagnostic capture does not mean no diagnostic pattern occurred.

## Separate smoke failures and remaining phases

The broad [smoke run 46096305068](https://github.com/dylandlr/hearthbound/actions/runs/46096305068),
attempt 1, completed with **11 planned smoke slots: seven successes and four failures**. Five
downstream comparison jobs were skipped, giving 16 total workflow jobs. All slots remain recorded;
skipped comparisons provide no acceptance evidence. Three failed slots passed Forge preflight and
source 8→7 / destination 0→1 wheat checks, then failed
`Wheat delivered but Sable not near destination`:

- TRAINED_MLP baseline: job 140828310624.
- SCRIPTED resource-probe-A: job 140828310824.
- SCRIPTED resource-probe-B: job 140828310785.

These are recurrences under [QA #348](https://github.com/dylandlr/hearthbound/issues/348). The five
relevant smoke/runtime blobs are identical at this head, the baseline and the historical furnace-fix
head; the evaluator patch does not run on this smoke path. This narrows attribution without declaring
the failures harmless. The old harness retains no insertion-time pose, so their individual causes
remain unknown. The separate arrival-witness PR349 is not yet integrated into this source.

The fourth failed slot was SCRIPTED resource-probe-C / seeded-v1,
[job 140828310817](https://github.com/dylandlr/hearthbound/actions/runs/46096305068/job/140828310817),
linked to the [QA #354 startup investigation](https://github.com/dylandlr/hearthbound/issues/354).
Forge preflight succeeded on its first attempt, but the startup step reported
`Minecraft server did not reach ready state within 12 minutes`. Asset downloads and run preparation
appear near the deadline in the retained log; the underlying cause is not established. No physical
trial outcome is verified for this slot, and its displayed SCRIPTED label does not establish policy
execution. It remains a startup failure, separate from the three post-transfer proximity failures.

The [final smoke diagnosis](evidence/civilization100/reliability-smoke-diagnosis.json) preserves all
16 job identities and conclusions, the 11-slot denominator, exact failure and inventory-success
excerpts, log hashes, and the five-path source comparison. Its startup artifact metadata is an upload
receipt from the job log; that ZIP was not independently downloaded or verified. The six independently
verified reliability archives described above belong to the separate five-world cohort.

The [citizen-death failure on PR349](C00_CITIZEN_LIFECYCLE_FAILURE.md) is another separately retained
world. The successful five-world cohort here does not erase it or provide a causal comparison between
branches. No native trial was rerun or replaced.

The evidence correction has completed implementation, independent review, local QA and its targeted
native pipeline validation. Integration and final acceptance remain open. The legacy frozen-policy
joined export was not reproduced; the current structured-journal native fixture remains scripted.
No learning advantage, causal communication benefit, 100-citizen operation or emergent specialization
is claimed. Relevant reference applications are recorded in the pinned reconciliation artifact;
routine input validation is justified by its reproduced defects and tests.
