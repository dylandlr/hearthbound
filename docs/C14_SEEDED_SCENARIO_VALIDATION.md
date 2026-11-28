# C14-01 seeded scenario validation

Recorded 27 November 2026 (America/Chicago). This report advances the planning and lifecycle
portion of [C14-01 / #233](https://github.com/dylandlr/hearthbound/issues/233). The physical
disruption, native sham and actor-isolation gates remain open.

## Published implementation

Draft [PR #352](https://github.com/dylandlr/hearthbound/pull/352) adds the separate scenario-v1
layer on top of the delivery core in [PR #234](https://github.com/dylandlr/hearthbound/pull/234).

| Identity | Value |
| --- | --- |
| Published head | `59772fbacd0cb0d056b29b70b96c91bc8f5cce6e` |
| Reviewed and published Git tree | `13f2d6d48f36637082f20a85f87c2dc9ac263b22` |
| Base | `7cf3730e64433849c56952f88780284f8f98b2a0` |
| Synthetic PR merge | `c8a93fcda8638660e2941939892b2ea86b5a076b` |
| Synthetic merge tree | `13f2d6d48f36637082f20a85f87c2dc9ac263b22` |

The [versioned contract](https://github.com/dylandlr/hearthbound/blob/59772fbacd0cb0d056b29b70b96c91bc8f5cce6e/docs/C14_SEEDED_SCENARIO_CONTRACT.md)
defines bounded immutable scopes, explicit targets, nonnegative 63-bit seeds, SHA-256 counter
draws with rejection sampling, canonical manifests and enforced journal identity. The initial
kinds are crop failure, mill failure and resource depletion. Treatment, sham and no-event arms
share latent choices while retaining distinct execution identities. Even an empty schedule is
bound to its complete configuration, mode, seed and original trial identity.

The generic scheduler-v2 implementation and journal format are unchanged. Coordinates and hashes
bind configured logical targets. They do not establish valid Minecraft height, loaded chunks,
observed block state, actual yield loss or a physically unchanged sham.

## Verified Java 17 execution

Both runs below used Temurin 17.0.21.1+2 with explicit `--release 17`. Each passed compilation,
**20 delivery Java contract groups, 11 scenario Java contract groups and 58 Python/cross-language
tests**: 41 existing tests plus 17 scenario tests. All four stage exit codes were zero.

| Run | Trigger / attempt | Artifact | ZIP bytes | Verified ZIP SHA-256 |
| --- | --- | --- | ---: | --- |
| [46096847430](https://github.com/dylandlr/hearthbound/actions/runs/46096847430) | Push / 1 | [15243940792](https://github.com/dylandlr/hearthbound/actions/runs/46096847430/artifacts/15243940792) | 5,780 | `9dbddef7ef231028eb116286295a8d74a1fa6e09326fcb73398664fc0d320b57` |
| [46096878816](https://github.com/dylandlr/hearthbound/actions/runs/46096878816) | Pull request / 1 | [15243613303](https://github.com/dylandlr/hearthbound/actions/runs/46096878816/artifacts/15243613303) | 5,773 | `22a8ba190fe7ab77ab8e4e6288748fd511c14e3f1e51973d678c55c5bcb59497` |

Both archives were downloaded and their byte lengths and SHA-256 digests matched GitHub metadata.
Each contains the manifest and four stage logs. All **14 source/document hashes and 16 fixture
hashes per run** match published Git blobs and the clean local published worktree. The expected
input inventories and all six Java compilation inputs were checked. Both manifests identify the
published head, clean initial inputs and no input changes during execution.

[The retained verification JSON](evidence/civilization100/scenario-ci-verification.json) records
each compared hash, stage, artifact identity and archive member digest. This is an artifact-content
verification, beyond observing a successful workflow badge. No rerun replaced a failed attempt.

## Independent review and preserved local failure

Independent review covered both implementations, canonical formats, bounds, fixtures, wrapper
identity and workflow changes. A separate calculation using explicit fixture values and the written
draw specification reproduced all nine latent-choice rows without importing either production
implementation. A wrapper probe rejected seven changed empty-schedule contexts and a foreign world,
reopened the original identity at cursor 5, and verified rejected opens left journal bytes unchanged.
The [review record](evidence/civilization100/scenario-independent-review.json) keeps these checks
separate from the unit-test totals.

Local functional development had already passed the same 20 + 11 Java groups and 58 Python tests
using the available Java 21 compiler module. The separate strict runner failed compilation with
`error: release version 17 not supported` because that local slim runtime lacked release-17 symbols;
all later stages were correctly marked not-run. CI supplied the full Java 17 toolchain. The CI pass
does not erase that local environment failure or relabel the development run as Java 17.

## References and acceptance boundary

The [source-to-decision record](https://github.com/dylandlr/hearthbound/blob/59772fbacd0cb0d056b29b70b96c91bc8f5cce6e/docs/C14_EVENT_SCHEDULER_REFERENCES.md)
applies the previously reviewed textbook lifecycle distinction, Drive monitoring reference,
Project Sid intended/observed outcome separation and MultiAgentBench measurement distinctions.
These support identity, evidence and evaluation decisions; the draw algorithm, byte format and
resource caps remain engineering choices validated by the tests.

## Separate broad smoke disposition

The complete head-associated workflow set finished with seven successful runs and one failed smoke
run. Both strict contract runs above, Forge compilation, packaging, cold dependency setup, ledger
regression and the simulator workflow succeeded. This is a workflow-status inventory; full native
artifacts from those separate suites were not all replayed here.

[Smoke run 46096878805](https://github.com/dylandlr/hearthbound/actions/runs/46096878805), attempt 1,
had **ten successful and one failed boot slot**, with all five downstream comparison jobs skipped.
The failed TRAINED_MLP/baseline-labeled
[job 140830156506](https://github.com/dylandlr/hearthbound/actions/runs/46096878805/job/140830156506)
verified source wheat 8→7 and destination 0→1, then failed the later 2.6-block proximity assertion.
This occurred in the direct chest-haul prologue before the later policy-trial dispatch; the job label
does not establish a trained-policy cause.

The failed [artifact 15243758135](https://github.com/dylandlr/hearthbound/actions/runs/46096878805/artifacts/15243758135)
matched its 168,982-byte API size and SHA-256
`b44a547f7c2b4fe77aed4107497f2d513972525d1d0bb6182691fc8a91be4fac`.
All eleven checkout logs identify the synthetic merge whose tree equals the published tree.
The relevant smoke workflow/script, haul runtime/controller/diagnostics, and complete existing
world/AI source subtrees are identical at this head, its scheduler base and the v0.23 candidate.
That establishes inherited source identity, not the failure's cause.

The [retained smoke diagnosis](evidence/civilization100/scenario-smoke-diagnosis.json) links the
recurrence to [QA #348](https://github.com/dylandlr/hearthbound/issues/348). It contains no final
position or health witness, so movement, disappearance, death and query/timing explanations remain
unresolved. No native disruption adapter ran in this workflow. The separate arrival-witness PR349
is not integrated into this branch. No rerun replaced the failure.

## Remaining acceptance

The manifests explicitly set Forge execution, native physical effects, native scope enforcement,
physical sham preservation and learned adaptation to false. Other compatibility workflows are
separate. This report does not declare all CI green, merge the stacked PRs, close C14-01, demonstrate
colony adaptation or satisfy the job-specialization milestone. The next physical crop-failure work
must measure actual harvest loss and prove its paired control unchanged.
