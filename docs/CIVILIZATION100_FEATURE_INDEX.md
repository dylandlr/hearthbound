# Civilization-100 feature and milestone index

**116 of 116 original feature IDs now have GitHub issues:** 110 newly published and six existing
issues preserved. Publication-time API readback found no missing or duplicate feature IDs. The 110
new bodies matched the original ticket and same-ID engineering worksheet, including their acceptance
clauses and ten initially unchecked engineering phases. Later evidence-based issue updates are tracked
separately. This is complete ticket publication, not completed feature development.

## Standing mission and working rule

Preserve the 100-generalist Minecraft/Forge/Create civilization mission, deep-learning-first development,
emergent occupations, and experimental disruptions. LLM controllers remain deferred. Authored fixtures,
RLS cost learning, scripted actions, green CI and inferred labels are not evidence of deep MARL or
civilization emergence by themselves.

For each ticket, consult only references that materially affect its design, implementation or evaluation.
Record source/version/page or section, finding, decision, test and transfer limits; distinguish primary
sources from reading reports and prior summaries. Routine mechanics may have justified research-not-
applicable entries. The source rule is committed in
[AGENTS.md at 7cf3730e](https://github.com/dylandlr/hearthbound/blob/7cf3730e64433849c56952f88780284f8f98b2a0/AGENTS.md),
with broader policy integration tracked by [PR #228](https://github.com/dylandlr/hearthbound/pull/228).

All new issues follow requirements, technical design, test design, implementation, code review, QA,
AI validation, Minecraft validation, integration and acceptance. Applicability must be explained;
creating a worksheet never certifies a phase complete. Refine epic dependencies into ticket-level
prerequisites and assign an owner before implementation.

## Standalone job-specialization milestone

[C04 — Job specialization, tracking issue #346](https://github.com/dylandlr/hearthbound/issues/346)
links all eight C04 children. It retains the 100-generalist starting condition, no assigned occupations,
quotas or role locks, inferred unknown/mixed occupations, voluntary work and career mobility, and the
original C04-08 gate: task entropy, mutual information, persistence and interdependence with metrics and
controls across **20 held-out seeds**, without fixed quotas. This is a milestone tracking issue; it does
not claim that a native GitHub milestone object was created or that specialization has been achieved.

## Epic coverage

| Epic | Scope | Feature tickets |
| --- | --- | ---: |
| C00 | Research and architecture | 5 |
| C01 | Cognition and identity | 7 |
| C02 | Embodied Minecraft actions | 8 |
| C03 | Multiagent learning | 9 |
| C04 | Job specialization | 8 |
| C05 | Construction | 8 |
| C06 | Technology discovery | 8 |
| C07 | Economy and industry | 7 |
| C08 | Personality and social life | 6 |
| C09 | Families and generations | 5 |
| C10 | Politics and institutions | 7 |
| C11 | Culture | 4 |
| C12 | Regions and settlements | 5 |
| C13 | Player interaction | 5 |
| C14 | Experimental disruptions and events | 15 |
| C15 | Validation and release | 9 |

## Current engineering work

- [C14-01 / #233](https://github.com/dylandlr/hearthbound/issues/233): the durable delivery core is
  implemented in [PR #234](https://github.com/dylandlr/hearthbound/pull/234). Java 17 compilation,
  20 Java contract groups and 41 Python/cross-language tests passed; existing Forge compatibility CI
  also passed. The separate seeded scenario layer in
  [PR #352](https://github.com/dylandlr/hearthbound/pull/352) now passes both strict Java 17 runs:
  20 delivery groups, 11 scenario groups and 58 Python/cross-language tests. Configured block scopes,
  paired plans and empty-control identities are bound; native scope enforcement, physical sham
  controls, physical adapters, actor isolation and final native acceptance remain open. See
  [the artifact verification](C14_SEEDED_SCENARIO_VALIDATION.md).
- [C00-02 / #227](https://github.com/dylandlr/hearthbound/issues/227): all five historical v0.23 artifacts
  were downloaded and verified, and all four raw trial histories were replayed. See
  [the baseline artifact audit](C00_BASELINE_ARTIFACT_AUDIT.md). The
  [branch ancestry audit](C00_BRANCH_ANCESTRY_AUDIT.md) covers 224 remote branches and 196 open PRs
  at its recorded snapshot. The bounded PR210 semantic mapping is complete, with a selective
  reliability-evidence correction in [PR #351](https://github.com/dylandlr/hearthbound/pull/351)
  and [QA #350](https://github.com/dylandlr/hearthbound/issues/350). Its unchanged five-world native
  pipeline passed, with all six archive digests verified and independent trusted-context replay
  matching the acceptance result. The [validation report](C00_RELIABILITY_VALIDATION.md) keeps the
  separate broad-smoke failures visible. Other relevant reconciliation and integration selection
  remain open.
- [PR #275](https://github.com/dylandlr/hearthbound/pull/275): closes the independent native-furnace
  counter comparison gap discovered during that audit. Four fresh native trials and clean restarts
  passed, with all artifact digests checked and physical audits independently replayed. The
  [validation report](C00_FURNACE_WITNESS_VALIDATION.md) retains those results and the separate smoke
  matrix failures; integration remains open.
- [QA follow-up #348](https://github.com/dylandlr/hearthbound/issues/348): the reviewed
  insertion-time arrival witness in [PR #349](https://github.com/dylandlr/hearthbound/pull/349)
  preserves inventory conservation and both existing geometry limits, retains later movement
  separately and rejects missing or foreign evidence. Local regressions and Java 17 Forge
  compilation passed. Nine of eleven declared smoke slots yielded independently verified native
  arrival records; two failed readiness before any arrival test. All nine later positions were
  still within the existing smoke radius, so these runs do not demonstrate a later out-of-range
  case or resolve the historical failure causes. The [validation report](C00_HAUL_ARRIVAL_VALIDATION.md)
  retains all eleven slots and both failed workflows. Integration remains open.
- [C14-02 / #323](https://github.com/dylandlr/hearthbound/issues/323): the next physical crop-failure
  feature keeps the original criteria: actual harvest loss measured and paired control unchanged.
  Its [reviewed proposed design and 22 named tests](C14_CROP_FAILURE_DESIGN.md) define bounded
  START-only destruction, real harvested-output measurement and a six-world treatment/sham/no-event
  cohort. Those tests have not run. Native context/world binding, tick ordering, witness durability
  and fixture resources remain design gates before implementation.
- [QA #353](https://github.com/dylandlr/hearthbound/issues/353): the
  [retained native lifecycle failure](C00_CITIZEN_LIFECYCLE_FAILURE.md) distinguishes completed
  material transfer from a later exact-UUID alive→dead→absent sequence. Required diagnostics failed;
  the physical cause and integration disposition remain open.
- [QA #354](https://github.com/dylandlr/hearthbound/issues/354): two PR349 slots and one PR351 slot
  timed out at server readiness after successful preflight. No arrival or policy result is inferred
  from these unavailable native observations. Stage-specific startup diagnosis and correction
  remain open; the existing deadlines were not extended and failed attempts were not replaced.

The QA follow-ups are additional defect tickets; they do not change the original 116-feature inventory.

The issue pages are authoritative for current progress. The phase notes below are a publication-time
snapshot, not an automated live status feed. All feature issues remained open at readback.

## C00 — Research and architecture

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C00-01 | Reference registry | [#229](https://github.com/dylandlr/hearthbound/issues/229) | Registry requirements; source inventory open |
| C00-02 | Branch baseline | [#227](https://github.com/dylandlr/hearthbound/issues/227) | Artifact audit verified; branch reconciliation open |
| C00-03 | Architecture contracts | [#230](https://github.com/dylandlr/hearthbound/issues/230) | Contract planning |
| C00-04 | Experiment protocol | [#231](https://github.com/dylandlr/hearthbound/issues/231) | Experiment protocol planning |
| C00-05 | Release governance | [#232](https://github.com/dylandlr/hearthbound/issues/232) | Release governance planning |

## C01 — Cognition and identity

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C01-01 | Identity and lifecycle | [#235](https://github.com/dylandlr/hearthbound/issues/235) | Planned |
| C01-02 | Local perception | [#236](https://github.com/dylandlr/hearthbound/issues/236) | Planned |
| C01-03 | Attention | [#237](https://github.com/dylandlr/hearthbound/issues/237) | Planned |
| C01-04 | Memory | [#238](https://github.com/dylandlr/hearthbound/issues/238) | Planned |
| C01-05 | Needs and affect | [#239](https://github.com/dylandlr/hearthbound/issues/239) | Planned |
| C01-06 | Belief and planning | [#240](https://github.com/dylandlr/hearthbound/issues/240) | Planned |
| C01-07 | Decision receipts | [#241](https://github.com/dylandlr/hearthbound/issues/241) | Planned |

## C02 — Embodied Minecraft actions

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C02-01 | Navigation | [#242](https://github.com/dylandlr/hearthbound/issues/242) | Planned |
| C02-02 | Block manipulation | [#243](https://github.com/dylandlr/hearthbound/issues/243) | Planned |
| C02-03 | Inventory and equipment | [#244](https://github.com/dylandlr/hearthbound/issues/244) | Planned |
| C02-04 | Food and survival | [#245](https://github.com/dylandlr/hearthbound/issues/245) | Planned |
| C02-05 | Farming and animals | [#246](https://github.com/dylandlr/hearthbound/issues/246) | Planned |
| C02-06 | Craft and smelt | [#247](https://github.com/dylandlr/hearthbound/issues/247) | Planned |
| C02-07 | Combat and defense | [#248](https://github.com/dylandlr/hearthbound/issues/248) | Planned |
| C02-08 | Forge/Create adapter | [#249](https://github.com/dylandlr/hearthbound/issues/249) | Planned |

## C03 — Multiagent learning

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C03-01 | Parallel environment | [#250](https://github.com/dylandlr/hearthbound/issues/250) | Planned |
| C03-02 | Baseline suite | [#251](https://github.com/dylandlr/hearthbound/issues/251) | Planned |
| C03-03 | Recurrent MAPPO | [#252](https://github.com/dylandlr/hearthbound/issues/252) | Planned |
| C03-04 | Hierarchical options | [#253](https://github.com/dylandlr/hearthbound/issues/253) | Planned |
| C03-05 | Reward ledger | [#254](https://github.com/dylandlr/hearthbound/issues/254) | Planned |
| C03-06 | Credit assignment | [#255](https://github.com/dylandlr/hearthbound/issues/255) | Planned |
| C03-07 | Training orchestration | [#256](https://github.com/dylandlr/hearthbound/issues/256) | Planned |
| C03-08 | Transfer parity | [#257](https://github.com/dylandlr/hearthbound/issues/257) | Planned |
| C03-09 | Learning gate | [#258](https://github.com/dylandlr/hearthbound/issues/258) | Planned |

## C04 — Job specialization

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C04-01 | Generalist initialization | [#259](https://github.com/dylandlr/hearthbound/issues/259) | Planned |
| C04-02 | Skill acquisition | [#260](https://github.com/dylandlr/hearthbound/issues/260) | Planned |
| C04-03 | Latent roles | [#261](https://github.com/dylandlr/hearthbound/issues/261) | Planned |
| C04-04 | Occupation inference | [#262](https://github.com/dylandlr/hearthbound/issues/262) | Planned |
| C04-05 | Comparative advantage | [#263](https://github.com/dylandlr/hearthbound/issues/263) | Planned |
| C04-06 | Labor market | [#264](https://github.com/dylandlr/hearthbound/issues/264) | Planned |
| C04-07 | Career mobility | [#265](https://github.com/dylandlr/hearthbound/issues/265) | Planned |
| C04-08 | Specialization gate | [#266](https://github.com/dylandlr/hearthbound/issues/266) | Planned |

## C05 — Construction

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C05-01 | Site survey | [#267](https://github.com/dylandlr/hearthbound/issues/267) | Planned |
| C05-02 | Design grammar | [#268](https://github.com/dylandlr/hearthbound/issues/268) | Planned |
| C05-03 | Material planning | [#269](https://github.com/dylandlr/hearthbound/issues/269) | Planned |
| C05-04 | Collaborative construction | [#270](https://github.com/dylandlr/hearthbound/issues/270) | Planned |
| C05-05 | Functional buildings | [#271](https://github.com/dylandlr/hearthbound/issues/271) | Planned |
| C05-06 | Roads and infrastructure | [#272](https://github.com/dylandlr/hearthbound/issues/272) | Planned |
| C05-07 | Repair and expansion | [#273](https://github.com/dylandlr/hearthbound/issues/273) | Planned |
| C05-08 | Town detection | [#274](https://github.com/dylandlr/hearthbound/issues/274) | Planned |

## C06 — Technology discovery

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C06-01 | Knowledge graph | [#276](https://github.com/dylandlr/hearthbound/issues/276) | Planned |
| C06-02 | Experiment interface | [#277](https://github.com/dylandlr/hearthbound/issues/277) | Planned |
| C06-03 | Discovery validation | [#278](https://github.com/dylandlr/hearthbound/issues/278) | Planned |
| C06-04 | Research strategy | [#279](https://github.com/dylandlr/hearthbound/issues/279) | Planned |
| C06-05 | Teaching and diffusion | [#280](https://github.com/dylandlr/hearthbound/issues/280) | Planned |
| C06-06 | Knowledge loss | [#281](https://github.com/dylandlr/hearthbound/issues/281) | Planned |
| C06-07 | Create technology | [#282](https://github.com/dylandlr/hearthbound/issues/282) | Planned |
| C06-08 | Novel mechanics boundary | [#283](https://github.com/dylandlr/hearthbound/issues/283) | Planned |

## C07 — Economy and industry

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C07-01 | Property and custody | [#284](https://github.com/dylandlr/hearthbound/issues/284) | Planned |
| C07-02 | Barter and prices | [#285](https://github.com/dylandlr/hearthbound/issues/285) | Planned |
| C07-03 | Contracts | [#286](https://github.com/dylandlr/hearthbound/issues/286) | Planned |
| C07-04 | Supply chains | [#287](https://github.com/dylandlr/hearthbound/issues/287) | Planned |
| C07-05 | Storage and transport | [#288](https://github.com/dylandlr/hearthbound/issues/288) | Planned |
| C07-06 | Industrial automation | [#289](https://github.com/dylandlr/hearthbound/issues/289) | Planned |
| C07-07 | Economic observability | [#290](https://github.com/dylandlr/hearthbound/issues/290) | Planned |

## C08 — Personality and social life

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C08-01 | Temperament | [#291](https://github.com/dylandlr/hearthbound/issues/291) | Planned |
| C08-02 | Learned personality | [#292](https://github.com/dylandlr/hearthbound/issues/292) | Planned |
| C08-03 | Relationships | [#293](https://github.com/dylandlr/hearthbound/issues/293) | Planned |
| C08-04 | Communication | [#294](https://github.com/dylandlr/hearthbound/issues/294) | Planned |
| C08-05 | Leisure and recreation | [#295](https://github.com/dylandlr/hearthbound/issues/295) | Planned |
| C08-06 | Social learning | [#296](https://github.com/dylandlr/hearthbound/issues/296) | Planned |

## C09 — Families and generations

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C09-01 | Reproduction and kinship | [#297](https://github.com/dylandlr/hearthbound/issues/297) | Planned |
| C09-02 | Inheritance | [#298](https://github.com/dylandlr/hearthbound/issues/298) | Planned |
| C09-03 | Child development | [#299](https://github.com/dylandlr/hearthbound/issues/299) | Planned |
| C09-04 | Households | [#300](https://github.com/dylandlr/hearthbound/issues/300) | Planned |
| C09-05 | Death and succession | [#301](https://github.com/dylandlr/hearthbound/issues/301) | Planned |

## C10 — Politics and institutions

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C10-01 | Collective proposals | [#302](https://github.com/dylandlr/hearthbound/issues/302) | Planned |
| C10-02 | Voting and delegation | [#303](https://github.com/dylandlr/hearthbound/issues/303) | Planned |
| C10-03 | Coalitions and leadership | [#304](https://github.com/dylandlr/hearthbound/issues/304) | Planned |
| C10-04 | Norms and enforcement | [#305](https://github.com/dylandlr/hearthbound/issues/305) | Planned |
| C10-05 | Negotiation games | [#306](https://github.com/dylandlr/hearthbound/issues/306) | Planned |
| C10-06 | EGTA | [#307](https://github.com/dylandlr/hearthbound/issues/307) | Planned |
| C10-07 | Institutional adaptation | [#308](https://github.com/dylandlr/hearthbound/issues/308) | Planned |

## C11 — Culture

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C11-01 | Cultural transmission | [#309](https://github.com/dylandlr/hearthbound/issues/309) | Planned |
| C11-02 | Collective identity | [#310](https://github.com/dylandlr/hearthbound/issues/310) | Planned |
| C11-03 | History and records | [#311](https://github.com/dylandlr/hearthbound/issues/311) | Planned |
| C11-04 | Recreation institutions | [#312](https://github.com/dylandlr/hearthbound/issues/312) | Planned |

## C12 — Regions and settlements

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C12-01 | Migration | [#313](https://github.com/dylandlr/hearthbound/issues/313) | Planned |
| C12-02 | Multiple settlements | [#314](https://github.com/dylandlr/hearthbound/issues/314) | Planned |
| C12-03 | Interregional trade | [#315](https://github.com/dylandlr/hearthbound/issues/315) | Planned |
| C12-04 | Diplomacy | [#316](https://github.com/dylandlr/hearthbound/issues/316) | Planned |
| C12-05 | Territory | [#317](https://github.com/dylandlr/hearthbound/issues/317) | Planned |

## C13 — Player interaction

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C13-01 | Citizen inspector | [#318](https://github.com/dylandlr/hearthbound/issues/318) | Planned |
| C13-02 | Colony interaction | [#319](https://github.com/dylandlr/hearthbound/issues/319) | Planned |
| C13-03 | Multiplayer | [#320](https://github.com/dylandlr/hearthbound/issues/320) | Planned |
| C13-04 | Gameplay onboarding | [#321](https://github.com/dylandlr/hearthbound/issues/321) | Planned |
| C13-05 | Modpack distribution | [#322](https://github.com/dylandlr/hearthbound/issues/322) | Planned |

## C14 — Experimental disruptions and events

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C14-01 | Event scheduler | [#233](https://github.com/dylandlr/hearthbound/issues/233) | Delivery-core QA verified; generation and native gates open |
| C14-02 | Crop failure | [#323](https://github.com/dylandlr/hearthbound/issues/323) | Planned |
| C14-03 | Resource depletion | [#324](https://github.com/dylandlr/hearthbound/issues/324) | Planned |
| C14-04 | Weather and hazards | [#325](https://github.com/dylandlr/hearthbound/issues/325) | Planned |
| C14-05 | Hostile mobs | [#326](https://github.com/dylandlr/hearthbound/issues/326) | Planned |
| C14-06 | Infrastructure failure | [#327](https://github.com/dylandlr/hearthbound/issues/327) | Planned |
| C14-07 | Specialist loss | [#328](https://github.com/dylandlr/hearthbound/issues/328) | Planned |
| C14-08 | Population shock | [#329](https://github.com/dylandlr/hearthbound/issues/329) | Planned |
| C14-09 | Trade interruption | [#330](https://github.com/dylandlr/hearthbound/issues/330) | Planned |
| C14-10 | Technology shock | [#331](https://github.com/dylandlr/hearthbound/issues/331) | Planned |
| C14-11 | Communication disruption | [#332](https://github.com/dylandlr/hearthbound/issues/332) | Planned |
| C14-12 | Political shock | [#333](https://github.com/dylandlr/hearthbound/issues/333) | Planned |
| C14-13 | Compound events | [#334](https://github.com/dylandlr/hearthbound/issues/334) | Planned |
| C14-14 | Recovery evaluation | [#335](https://github.com/dylandlr/hearthbound/issues/335) | Planned |
| C14-15 | Natural event director | [#336](https://github.com/dylandlr/hearthbound/issues/336) | Planned |

## C15 — Validation and release

| Ticket | Feature | Issue | Phase at publication |
| --- | --- | --- | --- |
| C15-01 | Evidence pipeline | [#337](https://github.com/dylandlr/hearthbound/issues/337) | Planned |
| C15-02 | Observatory | [#338](https://github.com/dylandlr/hearthbound/issues/338) | Planned |
| C15-03 | Performance budget | [#339](https://github.com/dylandlr/hearthbound/issues/339) | Planned |
| C15-04 | Persistence | [#340](https://github.com/dylandlr/hearthbound/issues/340) | Planned |
| C15-05 | Emergence audit | [#341](https://github.com/dylandlr/hearthbound/issues/341) | Planned |
| C15-06 | Integrated campaign | [#342](https://github.com/dylandlr/hearthbound/issues/342) | Planned |
| C15-07 | Long horizon | [#343](https://github.com/dylandlr/hearthbound/issues/343) | Planned |
| C15-08 | Release demo | [#344](https://github.com/dylandlr/hearthbound/issues/344) | Planned |
| C15-09 | Release package | [#345](https://github.com/dylandlr/hearthbound/issues/345) | Planned |

## Original artifacts and verification

The source packages are [civilization100_tickets.zip](https://chatgpt.com/library?file_id=libfile_3a0aa6252e508191900f383858fa0c43&account_id=personal)
and [civilization100_engineering_workflow.zip](https://chatgpt.com/library?file_id=libfile_129153ded8288191a26e5e969268ed79&account_id=personal).
Both remain unchanged. All 232 individual ticket/worksheet hashes were rechecked after publication.
The source ticket ZIP SHA-256 is `3059455bd5ed3f5882aff1214632f1cb73596d0abcd11500c88fcdf06ee086b1`;
the workflow ZIP SHA-256 is `62b1f4cc1fd64d68fc0a9f67d59a2ae9a925c53d8e128bc00a52358ea0bba63d`.

[The machine-readable issue map](evidence/civilization100/feature-issue-index.json) records IDs,
URLs, source hashes, publication disposition and readback hashes. Reused issue bodies can evolve
through authorized engineering work; the receipt hashes describe the captured readback, not a lock
against later updates. [The publication verification](evidence/civilization100/feature-publication-verification.json)
records the missing/duplicate/body-fidelity checks. No acceptance threshold was weakened to turn a
Planned item into a completed feature.
