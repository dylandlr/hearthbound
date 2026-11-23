# PA4 + MARBLE + Project Sid implementation contract

Status: **research/evaluation contract with scoped live adapters**. The v0.8 adapter records existing explicit report delivery and operator-triggered hauling; society experiments remain offline. This is an original Hearthbound adaptation; it is NOT a reproduction of Zhu et al.'s published MultiAgentBench scores and it is NOT autonomous real-Minecraft MARL deployment.

## v0.8 social-evidence extension

Project Sid is a co-primary design reference alongside MultiAgentBench/MARBLE. The verified sources and PA4 mappings are in [Project Sid and social evidence](PROJECT_SID_SOCIAL_EVIDENCE_V0_8.md). This extends, rather than weakens, the original evidence gates below.

The runtime retains a selected recipient-owned report snapshot in the pre-assignment hauling receipt. Explicit deliveries expose report/world/session IDs and endpoints. `scripts/social_communication_evidence.py` joins these actual fixture records to the accepted job and independently checked physical chest deltas. It rejects cross-world, wrong-recipient, duplicate, timeline and provenance conflicts. Unselected reports have **no measured other-use status**; selection is not proof of causal benefit. No communication is inferred from the colony board.

The four-citizen workflow runs three prespecified seeds in fresh, isolated runners with fail-fast disabled. `scripts/summarize_colony_trials.py` retains all planned trials, distinguishes terminal 3/4 accounting discrepancies from other failures and unknown/infrastructure outcomes, and reports observed-only Wilson intervals plus bounds including unknowns. The fixed arena and three seeds limit generalization. Old failures remain unresolved; retries must retain run attempt identity and never replace the original denominator.

## Canonical sources and version boundaries

- Kunlun Zhu et al., *MultiAgentBench: Evaluating the Collaboration and Competition of LLM Agents*, ACL 2025 (pp. 8580–8622), DOI [10.18653/v1/2025.acl-long.421](https://aclanthology.org/2025.acl-long.421/). Benchmark engine: https://github.com/ulab-uiuc/MARBLE, maintained code distinct from published paper; as of November 2026 the upstream README documents multiple bug fixes, including a repeated Minecraft task file.
- CSCE 631 PA4 Reading Reports, section P42 (MultiAgentBench) and synthesis; P06 (MAST failure taxonomy), P11 (multiagent debate), P32/P33 (empirical game-theoretic analysis). The source's core caution is to distinguish model/policy, coordination mechanism, outcome verifier and evaluator.
- Source-version hashes must be pinned before experiments; label new revisions explicitly. A repaired newer MARBLE checkout must not be reported as reproducing 2025 results.

## Architectural decisions

1. **Multiagent controller boundaries**: An agent's policy is its observation contract, individual state and memory, action mask, learned weights or scripted rule, plus sampling parameters. Topology and message delivery are properties of the environment/protocol. A star/tree/graph/chain swap changes who may observe which messages and can affect latency and compute, even with fixed weights.
2. **Keep the AI scope honest**: Hearthbound continues to defer LLM controllers. MARBLE's graph topology, milestone methods and diagnostic design transfer; its natural-language reasoning prompts and judge-generated C/P scores do not validate neural Minecraft citizens. Learn work allocation and coordination on grounded events first.
3. **Verifiable task outcomes**: A valid policy action, claimed completion and independent physical source/target/Create confirmation are distinct observations. Only the authoritative Forge journal or independently checked inventory delta can establish ground truth; `independentEvidence: true` in this offline evaluator is an **assertion by a trusted caller, not cryptographic proof**.
4. **Distinct objectives**: Preserve personal, colony and research rewards. Collect satisfaction, wealth, fairness, governance and political diversity as separate observables rather than forcing them into a premature single 'civilization quality' number.
5. **Communication safety**: Preserve speaker, recipient, time, scope, channel and delivery. Keep claims separate from independently verified observations; reserve mechanism/policy authority outside peer messages. No omniscient social planning.
6. **Organizations and politics**: Treat guilds, parties, cooperatives, councils, rivalries and other groups as *possible* outcomes of repeated interaction, resource allocation, local incentives and learning. Their names, ideology and survival are not preassigned success criteria; evaluate resulting institutions and membership uncertainty without claiming realistic human political preferences.

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
| P32/P33 EGTA | Freeze strategy/policy menu, model the full profile, measure unilateral deviations with sampled uncertainty | Leaderboard incorrectly called equilibrium |
| P04 NegotiationArena | Explicit resource/payoff objects, both role/seat orders | 'Agreed' incorrectly treated as fair, correct, or incentive compatible |
| P07 Visibility | Agent IDs, time-scoped activity, authorized observations, inspectable provenance | Can't reconstruct who knew or did what |
| P20/P23 incident analyses | Independent monitors, authority boundaries and scoped stopping rules | Unverified collective assumptions become operational authority |

## Experimental program

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
