# Hearthbound development principles

## Primary research references

For multiagent architecture, collaboration, competition, and evaluation work, consult these primary references together:

- **Altera.AL, Project Sid: Many-agent simulations toward AI civilization (2024)**: https://arxiv.org/abs/2411.00114v1 and https://github.com/altera-al/project-sid. Use its concurrent modules, action awareness, and measured social interactions as architectural and experimental references. Its public repository contains the report and assets, not a released runnable PIANO implementation.
- **Zhu et al., MultiAgentBench (ACL 2025)**: https://aclanthology.org/2025.acl-long.421/. Use its distinction between task outcomes, milestone participation, and coordination metrics.
- **MARBLE**, the implementation accompanying MultiAgentBench: https://github.com/ulab-uiuc/MARBLE. Treat the paper and the maintained engine as distinct versioned sources from the same research effort, not independent replications.

Read these alongside the user's CSCE 631 PA4 Reading Reports, particularly P42 (evaluation), P06/P11 (failure and disagreement), P28/P37 (memory and grounded action), P30/P34 (agent architecture), P04/P15/P19 (strategic interaction), and P32/P33 (empirical game theory). These are **architecture, evaluation, and mechanism references**; they do not authorize LLM controllers or prescribe a winning topology. The implementation contract is `docs/PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md`; verified source mappings and evidence limits are in `docs/PROJECT_SID_PA4_RESEARCH_FOUNDATION.md`.

## Engineering constraints

- Keep Hearthbound **Minecraft-first and fun-first**, with LLMs deferred while learning-based policies are validated. Keep exploratory society and benchmark modules isolated from production Forge behavior until gates pass.
- Model policies as complete observation/action/memory/learning configurations. Model star, tree, chain, graph, and optional learned network routing as communication **protocols** with explicit message delivery, budgets and topology changes.
- Separate intentions, commands accepted, agent testimony, and physically verified world changes. Only independent source/machine/output inventory witnesses establish task completion. Ensure durable provenance and no duplicated rewards/evidence.
- Record actual communication as separate send, delivery, recipient consumption, decision-use, and outcome events with stable world/run/message/citizen IDs. A social edge, proximity, message count, or outcome association alone is not evidence of causal benefit. Preserve failed, blocked, expired, duplicate, and unused messages.
- Keep fast Minecraft execution responsive while slower policy/memory work runs. Coordinate decisions through explicit state versions and action ownership; Project Sid's concurrency principle does not authorize off-thread Minecraft world mutation. Distinguish witnessed observations, peer claims, inferred beliefs, and bounded memories.
- Keep independent personal, collective and research reward domains; separate completion, participation, social diversity, economic welfare and coordination costs in reporting.
- Never equate consensus with correctness, a leaderboard with equilibrium, a simulated society with human social validity, or scripted actions with learned emergence.
- Report every failed, incomplete, rejected, and invalid trial in denominators. Aggregate uncertainty over **independent worlds**, not citizens inside one colony. Freeze seeds, training budgets, models, policies, protocol contracts, version hashes and all scored inputs.
- When studying political or organizational emergence, infer organizations from observed exchanges, affiliations, elections and institutions; do not preset mandatory party identities, personalities or government outcomes. Political topic preferences must remain mutable and evidence/context-dependent, not inferred from real human demographics.
- Use matched controls: no messages, shuffled messages, static/flexible roles, memory on/off, trained/untrained/script, independent policy seeds and changed communication structures. Add full ordered profile tests when analyzing strategic deviations; cite uncertainty and uncovered strategies.
- Test via standalone unit contracts, GitHub CI, actual Forge compilation and live physical acceptance **before** asserting an implemented runtime feature. Preserve existing Create/pickup/restart/conservation and four-citizen acceptance behavior. Do not silently merge stacked draft PRs.

## Relevant code and boundaries

- `experiments/marble-collaboration-bench.js`: pure scoped, verified-event milestone/communication scorer.
- `experiments/collaboration-evaluation-v0-2.js`: per-world provenance, matched-pair deltas and descriptive bootstrap estimates.
- `experiments/society-emergence.js`, `society-history.js`: standalone society hypotheses, not live Minecraft societal learning.
- `docs/PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md`: source distinctions, metrics and promotion gates.
- `docs/PROJECT_SID_PA4_RESEARCH_FOUNDATION.md`: primary Project Sid/MultiAgentBench/MARBLE references, PA4 mappings and transfer limits.

A paper's stated benchmark result is **not** a Hearthbound result. Pin the actual upstream revision, especially because MARBLE's November 2026 maintenance changed benchmark runner behavior and repaired scenario data.

## Reference relevance and continuity

For every ticket, consult the project references that materially affect its design, implementation,
or evaluation, including the configured [Drive refs folder](https://drive.google.com/drive/folders/1t-z8bDUgvEfu1eP_SfWEsJHrkuT4RMOY)
and supplied course/textbook sources where applicable. Record source identity/version and section/page,
the relevant finding, the resulting design decision, the validation it motivates, and its transfer limits.
Distinguish directly reviewed primary sources from reading reports and prior summaries. Mark routine
engineering details as research-not-applicable when appropriate; this is a relevance rule, not a source
quota. Do not insert unrelated information to make a ticket appear research-grounded.

Carry this rule through requirements, design, implementation, review, QA, and acceptance. The concrete
C14-01 mapping is [docs/C14_EVENT_SCHEDULER_REFERENCES.md](docs/C14_EVENT_SCHEDULER_REFERENCES.md).
[PR #228](https://github.com/dylandlr/hearthbound/pull/228) separately proposes
`docs/CIVILIZATION100_RESEARCH_POLICY.md` at commit `c97f1d42e101519ba625d0bc53d797564ab4cb5a`;
that policy PR is pending integration, not merged. This subsection records the user's standing rule
as a persistent project instruction in the repository; it makes no claim that account-level memory
was written.
