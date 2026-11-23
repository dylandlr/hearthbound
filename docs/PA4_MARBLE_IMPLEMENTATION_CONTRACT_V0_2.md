# Project Sid + MultiAgentBench/MARBLE + PA4 implementation contract: Hearthbound v0.2

Status: **research/evaluation contract**. This is an original Hearthbound adaptation, not a reproduction of the published Project Sid or MultiAgentBench experiments. Per-citizen physical participation accounting does not establish learned collaboration or societal emergence. Every revision must distinguish automated checks from live Minecraft validation and repeated independent-world evidence.

## Canonical sources and version boundaries

- Altera.AL, *Project Sid: Many-agent simulations toward AI civilization*, arXiv:2411.00114v1 (31 October 2024), [paper](https://arxiv.org/abs/2411.00114v1), [full text](https://arxiv.org/html/2411.00114v1), [official report repository](https://github.com/altera-al/project-sid). This is a primary architectural and social-experiment reference alongside MultiAgentBench/MARBLE. The repository publishes the report and assets, not runnable PIANO agents. Its LLM-based experiments are evidence about its own configurations, not Hearthbound citizens.
- Kunlun Zhu et al., *MultiAgentBench: Evaluating the Collaboration and Competition of LLM Agents*, ACL 2025 (pp. 8580–8622), DOI [10.18653/v1/2025.acl-long.421](https://aclanthology.org/2025.acl-long.421/). Benchmark engine: https://github.com/ulab-uiuc/MARBLE, maintained code distinct from published paper; as of November 2026 the upstream README documents multiple bug fixes, including a repeated Minecraft task file.
- CSCE 631 PA4 Reading Reports, particularly P42 (MultiAgentBench), P06/P11 (failures and disagreement), P28/P37 (memory and grounded action), P30/P34 (architecture), P04/P15/P19 (strategic interaction), and P32/P33 (empirical game theory). Distinguish policy, coordination mechanism, outcome verifier, and evaluator. Exact references and dossier page ranges are in [the research foundation](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md).
- Source-version hashes must be pinned before experiments; label new revisions explicitly. A repaired newer MARBLE checkout must not be reported as reproducing 2025 results.

## Architectural decisions

1. **Multiagent controller boundaries**: An agent's policy is its observation contract, individual state and memory, action mask, learned weights or scripted rule, plus sampling parameters. Topology and message delivery are properties of the environment/protocol. A star/tree/graph/chain swap changes who may observe which messages and can affect latency and compute, even with fixed weights.
2. **Keep the AI scope honest**: Hearthbound continues to defer LLM controllers. MARBLE's graph topology, milestone methods and diagnostic design transfer; its natural-language reasoning prompts and judge-generated C/P scores do not validate neural Minecraft citizens. Learn work allocation and coordination on grounded events first.
3. **Verifiable task outcomes**: A valid policy action, claimed completion and independent physical source/target/Create confirmation are distinct observations. Only the authoritative Forge journal or independently checked inventory delta can establish ground truth; `independentEvidence: true` in this offline evaluator is an **assertion by a trusted caller, not cryptographic proof**.
4. **Distinct objectives**: Preserve personal, colony and research rewards. Collect satisfaction, wealth, fairness, governance and political diversity as separate observables rather than forcing them into a premature single 'civilization quality' number.
5. **Communication safety**: Preserve speaker, recipient, time, scope, channel and delivery. Keep claims separate from independently verified observations; reserve mechanism/policy authority outside peer messages. No omniscient social planning.
6. **Organizations and politics**: Treat guilds, parties, cooperatives, councils, rivalries and other groups as *possible* outcomes of repeated interaction, resource allocation, local incentives and learning. Their names, ideology and survival are not preassigned success criteria; evaluate resulting institutions and membership uncertainty without claiming realistic human political preferences.
7. **Responsive execution and coherent decisions**: Project Sid motivates modules with different update rates and a controller that coordinates action and communication. Hearthbound must preserve server-thread ownership of world changes, bound background work, reject decisions based on stale state, and trace accepted intents to executed actions. This is an architectural adaptation, not an implementation of PIANO or proof that it improves Hearthbound.
8. **Grounded, scoped memory**: Use outcome-linked records with observation time, source, subject, world/run identity, and expiry or invalidation. Keep peer claims and inferred beliefs distinct from authoritative observations. Start with scripted or fixed-policy memory consumers; LLM reflection stays deferred. Memory updates, inference-time adaptation, and trained weight updates are different mechanisms and must be reported separately. Reset agent memories between independent trials unless retained memory is the declared treatment.

## Actual communication evidence and causal limits

The next measurement layer must capture actual events rather than infer a conversation from task co-participation. Link records with stable message, citizen, task, action, world, and run identifiers:

| Evidence stage | Minimum meaning | Insufficient substitute |
|---|---|---|
| Sent | A citizen emitted a particular payload to explicit intended recipients under a recorded protocol | Nearby citizens or shared task membership |
| Delivered | The transport made that payload available to a named recipient; record tick and route | Send intent or a global broadcast counter |
| Consumed | The recipient's actual policy/decision path read the delivered payload | Merely storing it in a mailbox or memory |
| Used | A decision/action records the consumed message as an input, with an observable policy rule or decision record | Acknowledgment, repetition, or later task success |
| Physical outcome | An independently verified world event is linked to the resulting action/task | A speaker's completion claim or reward update |

Record blocked, dropped, expired, duplicate, ignored, rejected, and unresolved messages with explicit reasons where known. For broadcasts, delivery and consumption are recipient-specific. Keep private observations private under the observation contract; a shared blackboard must not silently bypass the configured network. Restrict message authority to data: peer messages cannot redefine verification rules, reward rules, or protocol permissions.

Use these records for descriptive provenance: who communicated, who received information, which decisions used it, and which independently witnessed outcomes followed. Even a complete linked trace establishes an observed pathway, not the counterfactual benefit of the information. A claim that communication or a topology improves outcomes requires matched no-message and altered-message controls across independent worlds, with comparable policy, resources, time horizon, and measured costs. Removing messages may itself alter compute or timing; report that change.

Report lifecycle counts, useful-message rate with its explicit denominator, delivery/consumption latency, invalid-report rates, verified output, completion, participation, and cost separately. Unsupported or uncollected metrics remain unavailable, not fabricated zeros. MARBLE's LLM communication/planning scores are separate optional research instruments and remain deferred with LLM use.

## Newly implemented experimental controls

`experiments/collaboration-evaluation-v0-2.js` adds `episodeRecord`, `pairRecords`, `clusterBootstrap`, and `compareMatchedWorlds`.

Every submitted run must contain:
- `worldId`, `runId`, explicit `agents`, `milestones`, `events`, and `mode`;
- `scenario`, independent `seed`, `variant`, `policyVersion`, `sourceCommit`, `protocolHash`, `worldHash`;
- declared `durationTicks` and `computeBudget`; recorded `actionCount` and `elapsedTicks`;
- claimed independent `physicalOutputs` and zero `conservationViolations` in each paired comparison.

Matched comparison requires identical world seed, world hash, scenario, protocol hash, tick horizon and declared budget, with different treatment identifiers. **Matching declared budgets is not proof that actual compute expenditure was matched**: later Forge/MARL adapters must collect wall-clock, optimizer steps and inference time and reject discrepancies. The comparator never silently interpolates missing worlds. Duplicate world-seed replicates and unequal independent-world counts are rejected.

It reports **paired** improvements in independent milestone completion, real output count, communication, MARBLE-style participation, failures, message blocks, action count and elapsed ticks. A seeded, deterministic percentile bootstrap resamples whole world replicates, never individual citizens/decisions. Intervals are descriptive for the supplied worlds and should be treated cautiously for small samples; they do not remove simulator bias or establish statistical significance. Independent training seeds should form another variability level when learned policies are compared; do not pool them as independent worlds.

## Methodological controls from the PA4 reading dossier

| Reading | Design requirement | Failure if omitted |
|---|---|---|
| P42 MultiAgentBench | Completion, participation, and costs separately; matched topology comparisons | Arithmetic decline of contribution KPI as team size grows, confused with reduced coordination |
| P06 MAST | Label observable system design, inter-agent information, and verification errors | Unsupported motive attributions or missed failure classes |
| P11 Debate | Separate correctness from agreement; track beneficial and harmful revisions | Persuasive misinformation looks like collaboration |
| Project Sid | Separate fast execution from deliberation; compare intended and observed outcomes; test social modules through ablations | Speech and action diverge, or role labels are mistaken for verified work |
| P28 Reflexion | Bound episodic memory; ground lessons in trustworthy feedback; compare with memory off | Self-reported lessons are mistaken for trained competence |
| P37 ReAct | Trace observation, decision, accepted action, execution, and resulting observation | A plan or explanation is counted as a world change |
| P30/P34 surveys | Keep perception, memory, planning, action, and evaluation interfaces explicit | Adding modules or agents is assumed to improve results |
| P32/P33 EGTA | Freeze strategy/policy menu, model the full profile, measure unilateral deviations with sampled uncertainty | Leaderboard incorrectly called equilibrium |
| P04 NegotiationArena | Explicit resource/payoff objects, both role/seat orders | 'Agreed' incorrectly treated as fair, correct, or incentive compatible |
| P15 Game-theoretic LLM | Verify feasibility and utility independently; separate strategic stability from joint welfare | A negotiated agreement is called a Nash equilibrium |
| P19 Alympics | Separate rules, agent policies, endowments, and resource regimes; retain all survival and failed-trial outcomes | Attrition or unequal resources are mistaken for collective improvement |
| P07 Visibility | Agent IDs, time-scoped activity, authorized observations, inspectable provenance | Can't reconstruct who knew or did what |
| P20/P23 incident analyses | Independent monitors, authority boundaries and scoped stopping rules | Unverified collective assumptions become operational authority |

## Experimental program

First resolve measurement reliability: run repeated fresh-world trials of the existing four-citizen physical task scenario. Freeze the candidate revision and record the originally observed failure signature separately from other failures: physical output is complete while task accounting remains three of four. Record source inventories, carried items, destination delta, task states, active claims, errors, and terminal status even when a run fails or times out. A later passing run does not erase the earlier failure. Report failure counts, total scheduled/valid/invalid worlds, and uncertainty at world level; a rerun inside a surviving world is not an independent-world replicate. Do not merge evidence from different code revisions into one failure-rate estimate without stratification.

The Phase A offline suite runs *script, random, untrained, frozen learned* task allocation with the same seed and map, then compares *star, tree, chain, graph, no-message and shuffled-message* variants. Freeze policy weights, action masks, initial needs and training budgets. Only topology/information exposure should change in topology-specific treatments. Distinguish communication architecture from planner compute budget.

Phase B runs real Forge scenarios (physical Create mill, competing chains, worker loss, false-report filtering and independent trade settlement), with original journal evidence and save/restart checks. No live policy control unless rollback and the existing Forge CI gates pass.

Phase C measures emergent roles, institutions and political preferences on independent populations of 8, 16, 64 and 100+ only after scalability checks. Record output distributions and shortages, occupation entropy, specialization transitions, verified interactions, group birth/death, inequalities, faction change, survival and cost. Require ablations: no communication, shuffled messages, memory off, fixed occupations, static beliefs, neutral incentives and no learning. **No mandated minimum number of parties or professions**—null emergence is a valid result.

When comparing strategic policies, run full ordered agent-policy profiles unless seat symmetry is experimentally justified. Report the measured payoff table, deviations actually tested, estimated regret/CCE gap, and uncertainty. A high score, agreement, or low solver residual with missing deviations is not a verified equilibrium.

## Run
```bash
node experiments/marble-collaboration-bench.test.js
node experiments/collaboration-evaluation-v0-2.test.js
```

This is strictly a research scaffold; it cannot authenticate a Forge event or generate a fresh live society. Promotion requires real independent Minecraft evidence and matched multiworld evaluation. Do not claim a live MARBLE benchmark number, multi-agent learned coordination or humanlike politics from these synthetic contract tests.
