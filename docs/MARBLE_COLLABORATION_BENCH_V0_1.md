# Hearthbound collaboration benchmark (MARBLE-inspired) v0.1

## Attribution and scope
Research reference: Kunlun Zhu et al., **MultiAgentBench: Evaluating the Collaboration and Competition of LLM Agents**, ACL 2025, DOI 10.18653/v1/2025.acl-long.421, https://aclanthology.org/2025.acl-long.421/; implementation reference https://github.com/ulab-uiuc/MARBLE (MIT). **This is an original Hearthbound adaptation, not a MARBLE run, reproduction, or interchangeable leaderboard score.** MARBLE's LLM-specific prompt judging and scenarios are not imported into Hearthbound's LLM-deferred citizen controller.

The user's CSCE 631 PA4 reading dossier (P42, plus P06/P11/P32/P33) motivates independent outcome checks, explicit denominators, provenance, topology isolation, matched tasks, and uncertainty. The dossier notes MARBLE's 2026 maintenance fixes (including a formerly duplicated 100-task Minecraft file) and the published 2025 paper should be pinned separately from the maintained repository.

## Implemented pure scorer
`experiments/marble-collaboration-bench.js` accepts one independently generated, ordered, world/run-scoped event stream and four topology labels: `star`, `tree`, `chain`, `graph`. Only explicit `verified: true` milestones count. Unverified claims do not become completions. Names of contributors must match admitted agents. Replay IDs are deduplicated; conflicts and foreign-world events are rejected. Messages are counted and checked against permitted graph edges; blocked messages are a diagnostic, not evidence of task failure by themselves.

Separate quantities:
- `completionRate`: externally verified distinct successful milestones / total milestones.
- `participationKpi`: MARBLE-style sum of credited agent-milestone incidences / (number of agents * number of milestones). **This is NOT completion rate.** If at most k agents can be credited per milestone, its mathematical upper bound is min(1,k/N), even at perfect task completion.
- `participants`, `agentContributions`, `creditedIncidences`: workload and credit concentration.
- `failed`, `unresolved`, `invalidEvidence`, `duplicateEvents`: distinguish failure types and missing outcomes.
- `messages`, `validMessages`, `blockedMessages`, `messageCostPerCompleted`: crude interaction cost and protocol compliance.

No MARBLE `C-score`, `P-score`, or coordination aggregate is computed. The paper's LLM judge scores would require independent human validation; the user's P42 review notes Pearson human/model correlations 0.8057 (communication) and 0.2685 (planning). Those numbers are **literature measurements**, not Hearthbound results.

## Benchmark suite protocol (planned, NOT executed)
| Task ID | Hearthbound scenario | World-grounded success evidence | Stress condition |
|---|---|---|---|
| COLL-01 | Four-citizen acquisition → haul → Create mill → delivery | Source/cargo/destination counts, Create output witness, unique job receipts | One blocked route |
| COLL-02 | Two independent production chains | Distinct completed physical outputs, no ingredient duplication | Scarce shared inputs |
| COLL-03 | Citizen replacement | Work completes after operator removes one worker | Lost specialist |
| COLL-04 | Evidence sharing | Citizen chooses correct alternative after local peer message | False or delayed peer report |
| COLL-05 | Organization formation | Two-way verified distinct cooperation transactions | Shuffled/disabled communication |
| COLL-06 | Bargaining/trade | Independent inventory settlement with both participants' outcomes | Conflicting utility and asymmetric information |

Do not claim any planned scenario passes until a real Forge run with authoritative source evidence is recorded. For COLL-06, measure both players' payoffs separately and test both seat assignments.

## Experiment design
Run each scripted/random/untrained/learned policy under **matched world seeds, identical observation restrictions, equal action opportunities, equal horizon**, then vary one of the star/tree/chain/graph communication structures. Keep network messages distinct from physical outcomes and private knowledge. Explicitly record communication budget, elapsed Minecraft ticks, total client/server compute, actions and messages. Both no-communication and message-shuffled controls are needed; also compare fixed occupations vs adaptive work, memory reset vs persistence, and single vs multiple workers.

For scale, use 4, 8, 16, 64, 100+ only after capacity checks. Plot verified task completion and total physical throughput alongside participation KPI, messages per complete milestone, failure counts, distribution of contributions and organization diversity. Each **world seed** is a replicate; citizens in one world are not independent replicates. Compute uncertainty across worlds and avoid pooling dependent within-world decisions. Hold out seeds and map configurations; no policy promotion without confirmed physical conservation and previous Forge regression suite.

## Usage and limits
```bash
node experiments/marble-collaboration-bench.test.js
```
The script currently exercises synthetic fixture events to validate the pure scorer. It does not launch MARBLE, run Minecraft, train MARL, reconstruct a durable journal, or independently authenticate physical receipts. `verified` is asserted by the caller; a future explicit Forge adapter must establish it cryptographically/causally from already validated journals before use.

## Source-version and inference cautions
- Article: ACL 2025 DOI 10.18653/v1/2025.acl-long.421; P42 review is a separate secondary methodological analysis.
- MARBLE repo: maintained main as of November 2026. Pin commit, config, task hashes, model, evaluator, and scenario IDs before reproducing its results. Do not conflate repaired 2026 datasets with 2025 paper conditions.
- Paper reports graph does best *in the research scenario*, not all Minecraft tasks. The research-planning Figure 6 shows naive vs cognitive KPI 52.37 vs 49.87, so claimed 3% milestone improvement requires checking the exact comparator.
- P06 failure taxonomy: system design, inter-agent misalignment, and verification failures. This scorer catches only an observable subset; it does not infer hidden motives.
- P11: consensus is not correctness. P32/P33: rank is not equilibrium; strategy-deviation claims need independent measured payoffs including seat and topology conditions.
