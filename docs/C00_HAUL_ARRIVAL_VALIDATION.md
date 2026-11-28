# Native haul-arrival witness validation

Recorded 27 November 2026 (America/Chicago). Related:
[QA #348](https://github.com/dylandlr/hearthbound/issues/348),
[draft PR #349](https://github.com/dylandlr/hearthbound/pull/349), and
[C00-02 / #227](https://github.com/dylandlr/hearthbound/issues/227).

**Nine native arrival records passed independent replay. Two declared slots failed server readiness
before any arrival test ran.** The complete source-associated CI set finished with 26 successful and
two failed workflows; the second failed workflow concerns the separately retained citizen-death case.
This is not an all-CI-green or eleven-successful-world result.

## Change and preserved contract

The old smoke checked proximity after polling for inventory transfer. The reviewed correction captures
native citizen position and local container state immediately before and after the existing insertion,
bound to world, server session, dimension, citizen, job, assigned tick and endpoints. A separate
permission-2 query exposes that record and the current state. The verifier independently recomputes
both existing geometric limits: motor distance squared at most 6.25, and smoke distance squared at
most 2.6², using each check's original coordinate center.

The source 8→7 / destination 0→1 checks and original polling/readiness budgets are retained. A later
near position cannot rescue an invalid distant insertion. Later movement remains separately visible.
The observation does not change navigation, policy, settlement, reward or material-transfer authority.
Missing, malformed, stale, foreign and inconsistent evidence remains a failed acceptance gate.

Twenty-four focused arrival regressions passed, together with 36 existing motor-diagnostic tests,
the existing haul polling/RCON checks and pure geometry contracts. Independent review checked the
raw-response framing, exact integer identities, chronology and source tree. These tests are separate
from the native runs below.

## Source and Java 17 verification

| Binding | Verified value |
| --- | --- |
| Published head | `64c0fc63cb1940928c0b9abb53763f75abf7f1db` |
| CI merge checkout | `d39639856cb1a3417f03e27333f06c5730f9f6a4` |
| Published and merge tree | `5917af6e5df072b37b9281c6e3ffab17035f2fa3` |
| Native smoke run / attempt | [46096030530](https://github.com/dylandlr/hearthbound/actions/runs/46096030530) / 1 |
| Java 17 Forge compilation | [46096030697](https://github.com/dylandlr/hearthbound/actions/runs/46096030697) — passed |

The [compile record](evidence/civilization100/haul-arrival-forge-verification.json) checks the actual
Java major version, compile task and tree-equal merge checkout. The local geometry run used Java 21;
it was not represented as the Java 17 result.

## Every declared native slot

| Slot | Job | Artifact | Arrival evidence |
| --- | ---: | ---: | --- |
| Baseline SCRIPTED | 140827445252 | 15245091349 | Unavailable: readiness timeout |
| Baseline TRAINED_MLP | 140827444875 | 15243124995 | Verified pass |
| Resource A SCRIPTED | 140827445159 | 15243763091 | Verified pass |
| Resource A TRAINED_MLP | 140827445070 | 15243382744 | Verified pass |
| Resource A neural attention | 140827445172 | 15242734350 | Verified pass |
| Resource B SCRIPTED | 140827445128 | 15243985574 | Verified pass |
| Resource B neural attention | 140827445202 | 15243524158 | Verified pass |
| Resource C SCRIPTED | 140827445206 | 15243174434 | Verified pass |
| Resource C neural attention | 140827445135 | 15243966406 | Verified pass |
| Rapid D SCRIPTED | 140827445132 | 15242614252 | Verified pass |
| Rapid D neural attention | 140827445184 | 15245056007 | Unavailable: readiness timeout |

All eleven artifact ZIPs were downloaded. Independent review rehashed their bytes against the API
SHA-256 digests and sizes. All nine available arrival records passed raw-response replay, agreed with
the workflow-produced validation and matched protocol-source hashes at the published tree. Their
nine observed world UUIDs are distinct. Failed startup slots have no verified generated-world identity
and are not promoted into successful native world observations.

For all nine verified cases, native before/after insertion coordinates satisfy both preserved radius
rules. Destination inventory changes 0→1 while source inventory stays 7→7 across insertion; the
earlier pickup's 8→7 and later source/destination 7/1 observations are separately retained. Both
historically affected scenario labels—TRAINED_MLP baseline and SCRIPTED resource A—are included.

All nine later positions differ from insertion position, but all nine later raw proximity queries
pass and all nine later snapshots remain inside the original 2.6 radius. **There are zero native
cases here of valid insertion followed by a later position outside that radius.** Unit tests cover
that distinction; this cohort does not establish it as the cause of the historical failures.

The [complete native accounting](evidence/civilization100/haul-arrival-native-accounting.json)
retains every slot, bound identity, geometry distinction and replay result. The
[independent ZIP integrity record](evidence/civilization100/haul-arrival-artifact-integrity.json)
records every expected/actual digest and byte length. The workflow ended with nine successful and
two failed boot jobs; all five downstream comparisons were skipped. No pending slots remain.

## Startup failures retained separately

Both failed jobs logged the existing 12-minute readiness timeout before an arrival test. Preflight
reported successful compilation in 20m17s for rapid D and 20m8s for baseline SCRIPTED. Their launcher
logs ended around `prepareRunServerCompile`, without an observed readiness marker or application
exception. This identifies the last retained progress, not the underlying blocking cause.

- [Rapid-D diagnosis](evidence/civilization100/smoke-job-140827445184-diagnosis.json): artifact
  15245056007, 123,471 bytes, SHA-256
  `81bd826202fff1d530246e72eddb489b38b5039a6562207af1d81bac4f29cc76`.
- [Baseline diagnosis](evidence/civilization100/smoke-job-140827445252-diagnosis.json): artifact
  15245091349, 123,462 bytes, SHA-256
  `6fa958239a3be4f4c8a96b2b01b746bd1d27346b7dc8b793ad12179b52d9338e`.

[QA #354](https://github.com/dylandlr/hearthbound/issues/354) requires stage-specific diagnosis and
bounded retained evidence. No navigation, witness or infrastructure cause is inferred from a timeout.
The matrix labels do not prove that their later actor/policy trials executed.

## Separate lifecycle failure and remaining acceptance

The other failed workflow is [reliability run 46096030716](https://github.com/dylandlr/hearthbound/actions/runs/46096030716).
All original physical fixture scores report PASS, but world-02's required diagnostic capture is
incomplete after the exact UUID is observed alive, dead and absent. The
[verified summary](evidence/civilization100/haul-arrival-reliability-summary.json) preserves
`all_trials_passed:true` alongside required diagnostics false, four complete diagnostic worlds and
one incomplete world. The aggregate correctly failed. The
[detailed lifecycle record](C00_CITIZEN_LIFECYCLE_FAILURE.md) and
[QA #353](https://github.com/dylandlr/hearthbound/issues/353) retain the cause/integration questions.

No workflow was rerun, no native case was substituted, and no acceptance radius or observation budget
was relaxed. Implementation, independent review, local QA and Java 17 Forge compilation are complete.
Native arrival evidence is verified for nine of the eleven planned slots; readiness and lifecycle
failures still block a clean integration result. The two original historical proximity failures,
and recurrences on unchanged smoke branches, remain individually unexplained.

This observation/evidence correction establishes neither crash atomicity nor exactly-once physical
effects. It supplies no learned-policy advantage, long-term survival result, 100-citizen validation
or occupational-specialization result. The relevant reference distinction is between intended action,
accepted command and independently observed world effects; native evidence supplies the findings here.
