# C00-02: PR210 evidence reconciliation

Review date: 27 November 2026 (America/Chicago). This is a bounded reconciliation of [PR210](https://github.com/dylandlr/hearthbound/pull/210), not a review of its entire ancestor branch and not a decision to merge or close it. The evaluator repair is tracked in [QA issue #350](https://github.com/dylandlr/hearthbound/issues/350), under [C00-02 / #227](https://github.com/dylandlr/hearthbound/issues/227).

## Decision and scope

The existing communication journal and five-world reliability pipeline already cover the principal intent of PR210. Preserve those implementations. Importing the older text-receipt joiner or introducing another three-world pipeline would duplicate evidence paths and lose stronger current provenance checks.

This reconciliation makes a small change to the current reliability evidence boundary: malformed artifact types and duplicate JSON keys remain visible in a written five-slot summary, and workflow acceptance requires a trusted current run and attempt. No citizen observation, policy, learning, reward, dispatch, inventory operation, or outcome definition changes.

The first inspection considered only `real-four-citizen-colony.yml` and provisionally identified missing multiworld coverage. That hypothesis was corrected after reading the separate `real-colony-reliability.yml`, runner, summarizer, tests, and protocol. The existing cohort has **five** predetermined seeds, 43101–43105. It must not be replaced by PR210's older three-seed proposal.

Pinned inputs:

- Reviewed PR210 head: `99995505c9cf191a8cf983c43c22742696cd111d`.
- PR210 merge base: `b14a175e7d2ae1562649fc1ad4bc2546a8ad378f`.
- Target baseline: `a072519518db1458e8cb5aa1898aebd4ba93f03a`.
- The exact merge-base-to-head patch contains 17 changed paths. Its SHA-256 is `323d569a0f124a29f30592853f801bd6f2bff9fabb7d2c661e70a73855ff8e71`.
- The complete patch was read from the retained branch audit. Some legacy blobs are absent from the shared working clone; their identities below were read from the pinned Git tree. This review does not claim that a complete checkout of the old branch was compiled.

## Exact disposition of the 17 changed paths

| PR210 path | Proposed behavior in that delta | Current disposition |
| --- | --- | --- |
| `.github/workflows/pa4-marble-evaluation.yml` | Add tests for the legacy social joiner and three-world summarizer. | Keep the current offline evaluator. Native communication and five-world reliability have dedicated workflows and tests; do not add references to obsolete helper files. |
| `.github/workflows/real-four-citizen-colony.yml` | Expand the fixture to three seed jobs and aggregate their artifacts. | Superseded by `real-colony-reliability.yml`, which declares five worlds before build, checks the proposed head, uses isolated server processes, and summarizes after failure. Retain the original fixture workflow. |
| `.github/workflows/real-neural-report-haul.yml` | Run the legacy social-parser tests and add parser-related triggers. | Keep the existing frozen-policy fixture. `real-citizen-communication.yml` exercises the current structured journal and restart path. Exact frozen-policy journal export remains a validation limit described below; importing the old parser is not necessary to preserve the runtime hooks. |
| `AGENTS.md` | Add Project Sid, lifecycle distinctions, and complete-world denominators. | Already represented in current engineering principles and research foundation. Apply the user's per-ticket relevant-reference rule, including the separate instruction recorded at `7cf3730e64433849c56952f88780284f8f98b2a0`; do not claim that separate instruction commit is part of this pinned baseline. |
| `docs/PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md` | Describe the v0.8 social adapter and three-world pilot. | Preserve the current broader contract: delivery, consumption, decision use, physical outcome, and causal benefit remain distinct. Do not restore superseded v0.8 implementation claims. |
| `docs/PROJECT_SID_SOCIAL_EVIDENCE_V0_8.md` | Add source mappings and scoped social/reliability claims. | Its relevant principles are covered by `PROJECT_SID_PA4_RESEARCH_FOUNDATION.md`, `CITIZEN_COMMUNICATION_RECORDS_V0_1.md`, and `COLONY_RELIABILITY_TRIALS_V0_1.md`. This document supplies the bounded reconciliation and current evidence limits. |
| `scripts/export-four-citizen-benchmark.js` | Permit the three legacy fixture-seed labels. | Retain the existing strict per-citizen exporter. Current reliability provenance comes from generated seed and saved world identity, not the constant legacy fixture label. No new label allowlist is needed. |
| `scripts/export-four-citizen-benchmark.test.js` | Test the three allowed labels. | Retain the existing exporter acceptance tests; current reliability seed/identity tests cover its separate numeric-seed cohort. |
| `scripts/rcon_civilization_four_citizens.py` | Add a terminal marker and override the fixture seed from the environment. | Keep the fixture unchanged. `run_colony_reliability_trial.py` brackets physical probes with two terminal board reads and retains saved-world provenance. It explicitly disclaims the legacy fixture label as actual world identity. |
| `scripts/rcon_neural_report_haul.py` | Collect two text deliveries and attach the legacy joined social object. | Do not duplicate the structured journal with a frozen-policy-only regex joiner. Current report dispatch records lifecycle hooks; the current scripted native fixture separately joins the job to physical chest deltas. The literal old JSON export is not reproduced. |
| `scripts/score-verified-citizen-participation.js` | Accept the additional legacy seed labels. | Keep completion and participation scoring separate and fixture-scoped. The reliability denominator is handled by the five-world summarizer, not by enlarging this scorer's seed allowlist. |
| `scripts/social_communication_evidence.py` | Join delivery, selected report, job, and physical deltas from text receipts. | Superseded by `CommunicationJournal`, `CitizenCommunicationRecords`, and `rcon_citizen_communication.py`: structured lifecycle records, attempts, world/episode identity, bounded capacity, restoration, and independently checked inventory deltas. |
| `scripts/summarize_colony_trials.py` | Classify three planned worlds and report observed-only intervals plus missingness bounds. | Superseded by `summarize_colony_reliability.py`. The current pipeline has five prospective declarations, actual persisted identity, hash validation, two terminal reads, explicit failure categories, and a failing acceptance exit. Harden that current implementation for the residual gaps below. |
| `scripts/test_social_communication_evidence.py` | Reject conflicting receipt provenance and unsupported social claims. | Superseded by the pure Java journal tests and Python structured-chain validation tests, with separate current native acceptance and restart fixtures. Preserve attribution/causality limits. |
| `scripts/test_summarize_colony_trials.py` | Cover missing worlds, terminal failure classification, and conflicting success. | Current `test_colony_reliability.py` covers these concerns and stronger provenance cases. Extend it for the actual remaining malformed-input and current-attempt gaps. |
| `src/main/java/dev/hearthbound/world/CitizenKnowledgeExchange.java` | Add provenance fields to delivery text. | Equivalent source/world/session/recipient/report data already exist in structured communication exports. Keep the private inbox, freshness/range/session boundaries, failure beliefs, and send-attempt receipts. No Java port. |
| `src/main/java/dev/hearthbound/world/ReportHaulExperiment.java` | Re-read and copy the selected private report before assignment; add receipt text fields. | Current selected/assigned records already bind the immutable delivered message, decision, executor, job, and endpoints. Preserve current common dispatch hooks and policy behavior. Do not add a second receipt format or a new pre-assignment veto merely to support the legacy parser. |

## Current actor information and physical-evidence boundaries

`CitizenKnowledgeExchange` provides bounded recipient-owned reports. A peer report does not become a direct observation. Current policy evaluation uses those private reports, with world/session/freshness checks; the observer journal does not supply additional actor inputs. A withheld dispatch returns without recording fictitious report reads, and operator/shadow inspection does not manufacture use events.

`CommunicationJournal` separates `DELIVERED`, `READ`, `SELECTED`, `ASSIGNED`, and `PHYSICAL_COMPLETED`. `CitizenCommunicationRecords` retains message/decision/job/actor/world/episode provenance, send attempts, capacity denials, and recording errors. Physical completion is hooked to executor insertion and claim release. The native communication fixture separately checks source A 3→2, source B 1→1, and destination 0→1. An executor receipt is not itself independent inventory verification.

The journal is observational SavedData. Its ordinary save/restart checks do not establish crash-atomic coupling to inventories. Missing later lifecycle events remain unresolved; this journal alone is not a complete decision-usefulness denominator. The current native journal fixture is scripted. Both scripted and frozen-policy dispatch code have instrumentation, but this reconciliation does not claim a newly observed frozen-policy message-to-inventory trace. A complete association still does not establish a counterfactual communication benefit, learned collaboration, or an organization.

## Reproduced residual gaps and bounded changes

### Malformed evidence could suppress the denominator

At the pinned baseline, a file containing valid JSON `{"trial_id":["world-01"]}` produced `TypeError: unhashable type: 'list'` and no summary file. A known-slot record with `status: []` also reached unsafe set membership. Null validation-error lists and unhashable source/protocol fields exposed related paths. Existing tests covered unreadable JSON and some malformed nested evidence, but not these consumed field types.

The summarizer now checks object and consumed-field types before membership, hashing, aggregation, or diagnostic inspection. Malformed records with a usable exact trial ID become invalid evidence for that planned slot. Non-object and unassignable records remain explicit invalid artifacts. A duplicate remains an ambiguity even when one receipt is invalid; neither input ordering can turn it into a successful replacement. All five planned rows remain in the output, and ambiguous additional artifacts invalidate pooling.

The CLI also rejects duplicate JSON object keys before a later value can replace a conflicting earlier value. A loader-owned `artifact_sources` map connects `(kind, input_index)` to a relative artifact path. That map is collected outside artifact contents. A directory named `world-03` does not authorize assigning a null record to that trial.

### An internally consistent old attempt could be mistaken for the current attempt

The baseline rejected mixed run/attempt identities and mismatches between each result and its plan. It did not compare a consistent entire cohort against a trusted current workflow run and attempt. Supplying five internally matching old plans/results on the same source/protocol revision therefore left the descriptive all-pass result true.

The current workflow now supplies `--expected-run-id` and `--expected-run-attempt` from the GitHub workflow context, alongside the expected proposed-head commit. Every plan and result is compared with that context. Current checkout contents supply the expected protocol hash. A consistent older attempt is invalid for current acceptance, even when its commit and protocol match.

### Descriptive outcomes and acceptance are explicit

- `all_trials_passed` retains its existing descriptive meaning: every planned slot has a valid reported `PASS` and the cohort is unambiguous. It is not the acceptance decision.
- `validation_context` records the caller's expectations and reasons for missing, mismatched, or unverified context/plans. Offline API callers must obtain expectations independently of the artifacts; copying identity values from an artifact is not validation.
- `acceptance_passed` requires valid trusted source/protocol/run/attempt expectations, verified prospective plans, all descriptive trial outcomes passing, and every existing required motor-diagnostic gate passing.
- The CLI writes the summary before returning nonzero for incomplete, invalid, stale, failed, or descriptive-only analysis. It returns zero only for `acceptance_passed`.

An offline caller may inspect historical results without trusted workflow context. Such results are labeled `DESCRIPTIVE_ONLY`, and acceptance remains false. The evaluator is still a trusted-harness evidence validator, not a cryptographic authenticator. No arbitrary caller-supplied JSON can establish a native Minecraft observation merely by satisfying a unit-test schema.

## Acceptance cases for this change

| Case | Required result |
| --- | --- |
| Valid current five-world cohort with explicit trusted context, bound prospective plans, and required diagnostic verification | `acceptance_passed=true`; existing descriptive classification remains unchanged. |
| Same records with omitted or malformed trusted context | Historical description may be calculated; acceptance false with explicit context reasons. |
| All plans/results from one older run or attempt, on the same source/protocol | Five invalid planned outcomes, five unknown accounting outcomes, acceptance false. |
| Null, boolean, list, or object without a usable trial ID | Explicit unassigned invalid artifact; five planned rows retained; no fabricated identity from filenames. |
| Known trial with malformed status, source/protocol, world identity, boolean flags, validation-error list, or verified-diagnostic fields | Invalid evidence for that slot; no type exception suppresses the summary. |
| Duplicate exact trial ID where one receipt is malformed, in either order | Duplicate remains visible; no silent replacement; pooled observations become unknown. |
| Conflicting duplicate JSON keys in a plan or result | Artifact rejected before overwrite; relative source locator retained; denominator preserved. |
| Missing artifact, pre-build failure, infrastructure failure, invalid persisted identity, missing logs, or unverified diagnostics | Preserve existing separate statuses/unknown outcomes and required gates. |
| Four physical deliveries with the original stable 3-complete/1-assigned accounting signature | Preserve its original definition; do not merge it with the separately defined broader accounting event. |
| Communication lifecycle and participation regression suites | Existing private-information, identity, replay, chronology, and metric separation checks remain passing. |

Only these implementation paths change:

1. `scripts/summarize_colony_reliability.py`.
2. `scripts/test_colony_reliability.py`.
3. `.github/workflows/real-colony-reliability.yml`.
4. This reconciliation/design document.

## Relevant references and limits of transfer

The user's rule is to consult relevant project and `refs/` material for each ticket, record the finding→decision→test relationship, and avoid unrelated citation quotas. This review uses the source versions below. It does not claim a new account-memory write or broaden controller scope to LLMs. The broader policy proposal in [PR228](https://github.com/dylandlr/hearthbound/pull/228) remains separate from this change.

| Source actually consulted | Locator and version | Relevant finding and design/test consequence | Limit |
| --- | --- | --- | --- |
| Project Sid, primary technical report | [arXiv:2411.00114v1](https://arxiv.org/html/2411.00114v1), 31 October 2024, §§2.3 and 3.2; HTML section locators, not invented PDF pages. | Its action-awareness account distinguishes expected from observed outcomes. Keep report delivery, selected intent, accepted job, executor completion, and physical witness separate; preserve the structured lifecycle regression tests. | Architectural motivation. Its LLM-based results are not Hearthbound measurements or an instruction to adopt PIANO. |
| Zhu et al., MultiAgentBench, primary published paper | [ACL 2025 paper](https://aclanthology.org/2025.acl-long.421.pdf), §3.3, printed p.8584 / physical p.5. | Milestone participation, final task outcome, and coordination evaluation are distinct. Retain scoped participation tests and keep the independent-world reliability denominator separate from citizen contribution counts. | Its particular scenario metrics and role assignments do not establish emergent Hearthbound specialization or a universally better topology. MARBLE implementation and the article are versioned separately. |
| Chan et al., Visibility into AI Agents, primary paper held in the user's refs material | [arXiv:2401.13138v6](https://arxiv.org/abs/2401.13138v6), 17 May 2024, §§3.3–3.3.2, physical pp.7–8. Private locator: [Drive source](https://drive.google.com/file/d/1m7qqxJNFsoWmIaMXwzPhNBxum6HQjjUF/view), within the configured [refs folder](https://drive.google.com/drive/folders/1t-z8bDUgvEfu1eP_SfWEsJHrkuT4RMOY). | Activity logs support traceability and investigation; detail should serve the question being evaluated. Preserve structured lifecycle identity and make malformed artifact sources inspectable without expanding actor observation. | Logging does not authenticate inventory, prove causal benefit, or guarantee crash consistency. The local primary PDF version/pages were directly read; its hash does not assert byte identity with a Drive text extraction. |
| Supplied CSCE 631 PA4 dossier, secondary reading report | P06, physical pp.30–33 (printed report pp.1–4), and P42, physical pp.185–188 (printed report pp.1–4). Supplied file `01-PA4_Reading_Reports-2-.pdf`. | P06 separates observable failure patterns from causal explanations; P42 separates metrics and calls for exact evaluation versions. Retain invalid/infra/accounting categories and version-bound acceptance rather than treating an aggregate pass as a general capability result. | Secondary synthesis. This patch does not claim a fresh primary-paper review of every work cited by the dossier. |

The book's general messaging lifecycle material is not needed to justify these evaluator-only changes; no source was added simply to satisfy a reference count.

## Focused verification and remaining native gates

At baseline, the existing reliability suite passed 43 tests. After this change:

| Check | Observed local result | Scope |
| --- | --- | --- |
| `python3 -B -m unittest discover -s scripts -p 'test_colony_reliability.py'` | 54 tests passed. | Synthetic artifact/provenance/classification contracts, including CLI failures; no native-world count. |
| `python3 -B -m unittest discover -s scripts -p 'test_colony_motor_diagnostics.py'` | 29 tests passed. | Existing post-window diagnostic gate behavior. |
| `python3 -B -m unittest discover -s scripts -p 'test_citizen_communication.py'` | 2 test groups passed. | Structured communication-chain positive and adversarial cases. |
| `node scripts/export-four-citizen-benchmark.test.js` | Existing exporter contract assertions passed. | Fixture-scoped evidence export. |
| `node scripts/score-verified-citizen-participation.test.js` | 16 assertions passed. | Participation/completion separation. |
| Pure `CommunicationJournalTest` | 99 checks passed, compiled and executed using local Java 21.0.13.1. | The slim local runtime has no `javac` launcher; compilation used `java --module jdk.compiler/com.sun.tools.javac.Main`. This is not a Java 17 or Forge compilation result. |
| Independent reviewer input-type probe | 253 synthetic cases retained five planned rows without exceptions or acceptance lacking context. | Additional review evidence; not 253 native trials or additional committed unit-test methods. |

Java 17 CI remains the target. No Forge server was started for this reconciliation. A newly published exact head still requires its normal CI and all five native world artifacts with matching current run/attempt, verified prospective plans and required diagnostics. Earlier failed, missing, or invalid native trials remain part of their original cohorts. Passing these local checks does not close the historical accounting issue, prove communication benefit, or complete C00-02's other branch reconciliations.

## Source identities

The pinned PR210 tree contains these exact blob identities. `absent` filenames at the target are not proof of missing semantics; the disposition table names their replacements.

| Legacy path | PR210 blob SHA-1 |
| --- | --- |
| `.github/workflows/pa4-marble-evaluation.yml` | `5fc589a3f95eb88898bd936bf696dd82b66273dd` |
| `.github/workflows/real-four-citizen-colony.yml` | `3bd152c7bdd53e91b0deeb45e254b6bb070fc552` |
| `.github/workflows/real-neural-report-haul.yml` | `bd6bd07d61c93c355981c91d2cd45ca27ab31285` |
| `AGENTS.md` | `150048e3123a9f0f4b8292ed4e8687f7e34e95b5` |
| `docs/PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md` | `d160ece8b687f6b6788200a2d76b18d04ac7e967` |
| `docs/PROJECT_SID_SOCIAL_EVIDENCE_V0_8.md` | `a91c0eff7a665ba8a777fb94cb24959c852437af` |
| `scripts/export-four-citizen-benchmark.js` | `94071b537103a2b4e0427d91ffdb589299961c87` |
| `scripts/export-four-citizen-benchmark.test.js` | `6643ca75ff114e6654d071020506c28cedb69bec` |
| `scripts/rcon_civilization_four_citizens.py` | `b7e378e35cd79102e4872d9db04522fbf6931664` |
| `scripts/rcon_neural_report_haul.py` | `762b7096dd685acf2edb00a8b5a7f73264725b8e` |
| `scripts/score-verified-citizen-participation.js` | `2419777fb9f36f63ac79721bbc7d9f156d463a96` |
| `scripts/social_communication_evidence.py` | `3a9025dfe8f26c443c18e65b1840f4e258b53c27` |
| `scripts/summarize_colony_trials.py` | `0bb0a60406ff45e1088acff5d5ed3c82d7bfc15f` |
| `scripts/test_social_communication_evidence.py` | `cb254a9bb7a7c57c5590691faa6e2ab81cfac2f5` |
| `scripts/test_summarize_colony_trials.py` | `02f273d3090b60c82a45c338de18abb2bbfcd918` |
| `src/main/java/dev/hearthbound/world/CitizenKnowledgeExchange.java` | `078606817c7986ba8c8f8edc992913cfe21d5ce6` |
| `src/main/java/dev/hearthbound/world/ReportHaulExperiment.java` | `e2bd5158f20ed01a53377e7b492578890b3d4f89` |

Read source-file SHA-256 values:

| Source | SHA-256 |
| --- | --- |
| Published MultiAgentBench PDF | `035f673b459aecad0b7fa0fdac21dd9585f644cb29fba45f4ecbceef28f81eb5` |
| Chan v6 primary PDF | `5fa0de17952151268dc561b2100a0f9e3dd6392b7c92e5b56c1afeb1dc0416a9` |
| Supplied PA4 dossier | `ea658537d963e25924e2ab9d37950cece375884df45a1cb23fc1e9302583d3bd` |

Implementation bytes at the end of the focused local review, before publication:

| Changed implementation artifact | SHA-256 |
| --- | --- |
| `scripts/summarize_colony_reliability.py` | `eb18e8527eb285934c0c9283a69a6fdd6782c844bd3a602d30a09e443be293a6` |
| `scripts/test_colony_reliability.py` | `eac15b75d50e9cac88944d4e9e1ba451b74b33eac8a35a23e8c30cdc3fa4c18f` |
| `.github/workflows/real-colony-reliability.yml` | `69a59c27367312071a27154ce60f94c0b766771b90e8ed33c72d65e1cd600161` |

These hashes identify reviewed source bytes, not successful native execution. No primary-source PDFs are copied into the repository.
