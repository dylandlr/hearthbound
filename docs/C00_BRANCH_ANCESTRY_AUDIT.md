# C00-02 remote ancestry audit and reconciliation triage

Snapshot: 27 November 2026 (user date), after PR #347 was created at `711bb0f4ed983945f2903b935eec2e3391bbd885` and before later documentation updates. Parent: [C00-02 / #227](https://github.com/dylandlr/hearthbound/issues/227).

## Decision-ready finding

Keep `a072519518db1458e8cb5aa1898aebd4ba93f03a` (`feat/renewable-village-economy-v0-23`, draft [PR #226](https://github.com/dylandlr/hearthbound/pull/226)) as the pinned development baseline candidate. The graph supports this choice: 158 other remote branches are its ancestors; the only four descendants are the intentionally isolated research-policy, scheduler, furnace-witness, and ticket-index branches. This is **not** a declaration that all prior work has been integrated or behaviorally preserved.

Default `main` remains `fbde0300ccf07509bbbdca4f3deb436d19ad15ca`: 0 commits ahead and 1129 behind the candidate. Selecting main would discard the current working runtime history from the checkout, while selecting an old numerically larger branch name would select a divergent lineage. No branch was merged, reset, switched, deleted, or pushed during this audit.

## Inventory and definitions

| Ancestry relative to candidate | Remote branches | Open PRs |
| --- | ---: | ---: |
| Covered ancestor | 158 | 155 |
| Candidate itself | 1 | 1 |
| Candidate descendant | 4 | 4 |
| Diverged | 61 | 36 |
| Total | 224 | 196 |

- GitHub open-PR pagination returned 100 records on page 1 and 96 on page 2. There are 170 draft and 26 non-draft PRs, with 195 distinct head SHAs; #25 and #26 share one head.
- Every observed PR head was available in the independent clone. No PR head differed from its matching remote branch at this snapshot.
- `covered ancestor` means commit reachability, **not** proof that its behavior survives later edits or that its acceptance criteria remain valid.
- `ahead / behind` below means commits unique to the branch / unique to the candidate. Unique patch statistics compare the common merge base with the branch head, avoiding the misleading large endpoint diff caused by all later candidate development.
- The 61 divergent branches reduce to 20 maximal divergent tips. Seven maximal tips have no open PR. Tip coverage can overlap and is not a disjoint partition.

## Isolated descendants (not a consolidated integration base)

| PR | Exact head | Ahead / behind | Unique patch |
| --- | --- | --- | --- |
| [#228](https://github.com/dylandlr/hearthbound/pull/228) | `c97f1d42e101519ba625d0bc53d797564ab4cb5a` | 1 / 0 | 1 file changed, 19 insertions(+) |
| [#234](https://github.com/dylandlr/hearthbound/pull/234) | `7cf3730e64433849c56952f88780284f8f98b2a0` | 3 / 0 | 15 files changed, 2640 insertions(+) |
| [#275](https://github.com/dylandlr/hearthbound/pull/275) | `8206ca0e3bb6668e896ecb03d7bd1b0269ae7f50` | 1 / 0 | 3 files changed, 176 insertions(+), 1 deletion(-) |
| [#347](https://github.com/dylandlr/hearthbound/pull/347) | `711bb0f4ed983945f2903b935eec2e3391bbd885` | 1 / 0 | 7 files changed, 3051 insertions(+) |

These branches remain separate draft PRs. The scheduler adds an experiment Java package; that source-path fact is not evidence of native actor integration. The furnace-witness branch changes validation, not the world runtime. Its CI outcome belongs in the separate native evidence audit.

## Meaningful divergences

| PR | Exact head | Ahead / behind | Unique patch |
| --- | --- | --- | --- |
| [#210](https://github.com/dylandlr/hearthbound/pull/210) | `99995505c9cf191a8cf983c43c22742696cd111d` | 2 / 35 | 17 files changed, 441 insertions(+), 13 deletions(-) |
| [#129](https://github.com/dylandlr/hearthbound/pull/129) | `507cfc86f091074aa09d3a882854397fa3ca39f0` | 4 / 668 | 4 files changed, 318 insertions(+) |
| [#78](https://github.com/dylandlr/hearthbound/pull/78) | `903baf2db31258a3914da5738e8eab530a270b4c` | 3 / 1129 | 3 files changed, 101 insertions(+) |
| [#75](https://github.com/dylandlr/hearthbound/pull/75) | `c435a414d67dfb1f9515dc4e971488a7593ef375` | 457 / 930 | 200 files changed, 10422 insertions(+), 42 deletions(-) |
| [#76](https://github.com/dylandlr/hearthbound/pull/76) | `4c782621e10ee16c6c9a7dd6480b7edef375ed04` | 386 / 1129 | 170 files changed, 6907 insertions(+), 7 deletions(-) |
| [#4](https://github.com/dylandlr/hearthbound/pull/4) | `2bd0a51bd55fb54d138ca3361d2769fb3e226355` | 179 / 1129 | 119 files changed, 8816 insertions(+), 6 deletions(-) |
| [#35](https://github.com/dylandlr/hearthbound/pull/35) | `59e585e44f302220f436396d1f94438a2a6ffc02` | 127 / 930 | 88 files changed, 5135 insertions(+), 28 deletions(-) |

### PR #210: Record citizen report-to-haul evidence and repeat fresh-world reliability trials

Highest-priority unresolved nearby change. Five added social-evidence/reliability files are absent at candidate; two Java runtime files and acceptance workflows differ. Requires a scoped port/reconciliation against current communication and evaluation contracts.

Added paths absent at the candidate:

- `docs/PROJECT_SID_SOCIAL_EVIDENCE_V0_8.md`
- `scripts/social_communication_evidence.py`
- `scripts/summarize_colony_trials.py`
- `scripts/test_social_communication_evidence.py`
- `scripts/test_summarize_colony_trials.py`

### PR #129: feat: shared event-driven colony perception ledger and machine-vision interface roadmap (v0.10.9)

Four added shared-perception files are absent at candidate. Review observation ownership and actor information boundaries before adoption; filename/ancestry does not establish architectural compatibility.

Added paths absent at the candidate:

- `.github/workflows/shared-perception-ledger.yml`
- `docs/SHARED_PERCEPTION_AND_VISION_ROADMAP_V0_10_9.md`
- `src/main/java/dev/hearthbound/perception/SharedPerceptionLedger.java`
- `src/test/java/dev/hearthbound/perception/SharedPerceptionLedgerTest.java`

### PR #78: feat: processing evidence gate for First Mill research (v0.4)

Three added processing-evidence gate files are absent at candidate. Compare intent with current causal evidence and physical witnesses; do not reintroduce an old parallel authority automatically.

Added paths absent at the candidate:

- `docs/PROCESSING_EVIDENCE_GATE_V0_4.md`
- `src/main/java/dev/hearthbound/evidence/ProcessingEvidenceGate.java`
- `src/test/java/dev/hearthbound/evidence/ProcessingEvidenceGateTest.java`

### PR #75: v4.5 Verify physical completion before accepting released source claim

Large October alternative stack: 200 unique changed files; includes old work dispatch, research/teaching, learning persistence, and tactical client modules. 41 divergent branch heads are ancestors of this tip. Preserve for capability triage; no wholesale merge recommendation.

### PR #76: build: pin Create 6.0.8 for Hearthbound Forge 1.20.1

Large October alternative Create/integration/research stack; 170 unique changed files. Current v0.23 uses a different runtime lineage. Requires per-capability comparison, not version-name-based selection.

### PR #4: First Mill sharing and agent-learning foundation

Large October First Mill/client/workshop/policy stack; 119 unique changed files. Different package structure and integration history. Not a safe replacement base without a separate compatibility audit.

### PR #35: Add physical survival decisions and sustained citizen work

October survival/work stack with 88 unique changed files. Three divergent branch heads are ancestors of this tip. Presence of survival source files does not establish currently accepted behavior.

## Small corrections already represented in the candidate

| PR | Evidence inspected | Remaining limit |
| --- | --- | --- |
| [#134](https://github.com/dylandlr/hearthbound/pull/134) | Sole changed file `LivePerceptionReceipts.java` has the same Git blob ID at the candidate. | Commit ancestry still differs; this is file-content evidence. |
| [#146](https://github.com/dylandlr/hearthbound/pull/146) | Sole changed file `CitizenAttentionJournal.java` has the same Git blob ID at the candidate. | Commit ancestry still differs; this is file-content evidence. |
| [#138](https://github.com/dylandlr/hearthbound/pull/138) | Inspected candidate sampler lacks the duplicate local declarations removed by the unique patch. | Later sampler changes mean the whole file is not identical; no new runtime test was run. |
| [#177](https://github.com/dylandlr/hearthbound/pull/177), [#178](https://github.com/dylandlr/hearthbound/pull/178) | Inspected floor placement, AI freeze/restore, and callback/inventory checks in candidate `rcon_sable_first_mill.py`. | Semantic patch triage, not a rerun of those native scenarios. |
| [#194](https://github.com/dylandlr/hearthbound/pull/194) | Unique patch adds three lines in `docs/wfx-audit.md`, absent at candidate. | Documentation-only reconciliation remains; not a competing runtime baseline. |

## Maximal divergent tips

| Branch | Exact SHA | Open PRs | Divergent branch heads reachable |
| --- | --- | --- | ---: |
| feat/society-foundation-experiment-v0-9 | `02ad74e8c55c7d5207386b4cb280578c22851643` | None | 1 |
| test/haul-to-study-rcon-20261018 | `0fc5cc1985a103376ebae7517b63b0307fa732fb` | None | 1 |
| fix/forge-ci-coverage-20261018 | `17beb5cb7be07ed175394f79c9530ef01538b1af` | None | 1 |
| feat/real-mill-outcome-probe-v0-15-6 | `25cdda0094025e289904868f4a3dc46ae2d77f64` | [#177](https://github.com/dylandlr/hearthbound/pull/177) | 1 |
| feature/first-mill-foundation | `2bd0a51bd55fb54d138ca3361d2769fb3e226355` | [#4](https://github.com/dylandlr/hearthbound/pull/4) | 1 |
| test/real-outcome-restart-v0-15-7 | `3f5300072cdff43d1f8ba30c077621cf7140d2c8` | [#178](https://github.com/dylandlr/hearthbound/pull/178) | 1 |
| feat/create-forge-dependency-v1-2 | `4c782621e10ee16c6c9a7dd6480b7edef375ed04` | [#76](https://github.com/dylandlr/hearthbound/pull/76) | 1 |
| test/multi-citizen-haul-20261018 | `503673f225ba1ec1aa56ed86bcae43536e6ed57f` | None | 1 |
| experiment/shared-perception-ledger-v0-10-9 | `507cfc86f091074aa09d3a882854397fa3ca39f0` | [#129](https://github.com/dylandlr/hearthbound/pull/129) | 1 |
| feat/survival-instinct-loop | `59e585e44f302220f436396d1f94438a2a6ffc02` | [#35](https://github.com/dylandlr/hearthbound/pull/35) | 3 |
| experiment/citizen-source-memory-v0-11-3 | `7e52d17747ac66ebd694c0e9adae2ad6b4aa3ba9` | [#134](https://github.com/dylandlr/hearthbound/pull/134) | 1 |
| feat/discover-wheat-source-v0-8-0 | `8835297227a0edf438702595650022d0704b76bc` | None | 1 |
| feat/processing-evidence-gate-v0-4 | `903baf2db31258a3914da5738e8eab530a270b4c` | [#78](https://github.com/dylandlr/hearthbound/pull/78) | 1 |
| experiment/social-communication-evidence-v0-8 | `99995505c9cf191a8cf983c43c22742696cd111d` | [#210](https://github.com/dylandlr/hearthbound/pull/210) | 1 |
| feat/discover-library-work-v0-7-9 | `ac5a6e2793e45cb61896c6b2dfa0c73d33d9f90b` | None | 1 |
| fix/claim-release-message-v4-5 | `c435a414d67dfb1f9515dc4e971488a7593ef375` | [#75](https://github.com/dylandlr/hearthbound/pull/75) | 41 |
| experiment/selective-citizen-attention-v0-11-7 | `c592933f04fd6c2cf5d632c5264ffd511b74efb8` | [#138](https://github.com/dylandlr/hearthbound/pull/138) | 1 |
| wfx-docs | `cc62ca8a36619e6139dc4b5f232e5cf53cbfd373` | [#194](https://github.com/dylandlr/hearthbound/pull/194) | 1 |
| experiment/attention-run-finalization-v0-12-5 | `d9bf3518aae96f6a04e2767d0a0ae59e093134b6` | [#146](https://github.com/dylandlr/hearthbound/pull/146) | 1 |
| feat/colony-job-board-v0-8-2 | `e9d1802caffa15e0d301fad7661f61ad6d13f943` | None | 1 |

## Reconciliation actions

1. Record the candidate SHA as the baseline under evaluation; keep new work on isolated descendants until integration gates are met.
2. Review PR #210 first as the nearest independent runtime/evidence change. Port only justified deltas into the current communication and trial-evidence contracts, with focused regression tests. Its 17-file unique-change inventory and explicit candidate-path presence/blob comparisons are in the retained summary JSON; patch text is not embedded.
3. Preserve the legacy tips for feature archaeology: compare old teaching, technology, observation, work, and client capabilities against current tickets. Do not equate authored work boards or old policy classes with accepted emergent specialization.
4. Mark the five small corrective PRs above as content-reconciliation candidates supported by the stated evidence; do not silently merge or close them from this graph audit.
5. Keep native artifact validation, branch integration strategy, and acceptance separate. This audit advances C00-02 ancestry coverage but does not close the whole ticket.

## Method, artifacts, and limits

- Sources: `GET /repos/dylandlr/hearthbound/pulls?state=open&per_page=100&page=1` and page 2; independent bare filtered clone of the public repository; exact Git commit/tree/blob objects. Large legacy diff counts use GitHub `compare/<merge-base>...<head>?per_page=1&page=1`; each API file count matched the independently enumerated Git tree delta.
- Commands: `git for-each-ref refs/heads`, `git merge-base --is-ancestor`, `git rev-list --left-right --count`, `git merge-base --independent`, `git diff --no-renames --name-status`, and selected `git diff --shortstat` / exact blob comparisons.
- The initial read-only fetch in the shared checkout failed with `pack has 17 unresolved deltas`. No repair was attempted. A separate bare clone succeeded and supplied complete graph classification. An additional legacy blob read from the shared object store failed; those four legacy statistics were obtained from the GitHub compare API instead. Neither failure invalidates the independently cloned graph results.
- [The retained graph inventory](evidence/civilization100/baseline-ancestry-inventory.json) contains all 224 branch rows and 196 open PR rows, exact heads, SHA-based classifications, merge bases and comparison counts. It omits repetitive endpoint file lists; [the decision summary](evidence/civilization100/baseline-ancestry-summary.json) retains selected unique changed paths and file/blob comparisons. The inventory records the original scratch audit hash for provenance, without implying that scratch analysis is a permanent downloadable artifact.
- This is a point-in-time remote inventory. It excludes local uncommitted changes and does not continuously watch later updates. Open PR status is not proof of recent activity. No new native execution, full semantic review of every branch, security audit, or merge approval is claimed.
- Current source files were inspected only for the stated narrow correction checks. Files absent at a path can have later replacements elsewhere; absence is a triage signal, not proof that the capability is wholly missing.
