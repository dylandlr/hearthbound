# Hearthbound development principles

## Primary research references

For multiagent collaboration, competition, and evaluation work, consult **Altera.AL, Project Sid: Many-agent simulations toward AI civilization**, [original technical report v1](https://arxiv.org/html/2411.00114v1) and [author repository](https://github.com/altera-al/project-sid), alongside **Zhu et al., MultiAgentBench (ACL 2025)** (https://aclanthology.org/2025.acl-long.421/) and the maintained MARBLE repository (https://github.com/ulab-uiuc/MARBLE), *alongside* the user's CSCE 631 PA4 Reading Reports (especially P42, P06, P11, P28, P19, P32, P33). This is an **evaluation and mechanism reference**, not an instruction to adopt LLM controllers or copy a particular communication topology. The detailed Hearthbound implementation contract is `docs/PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md`.

Project Sid is a primary architectural hypothesis reference (memory, social awareness, action coherence, specialization), not evidence of Hearthbound capabilities. Its public repository supplies a report, not a reproducible PIANO implementation. See `docs/PROJECT_SID_SOCIAL_EVIDENCE_V0_8.md` for verified source versions, PA4 page references, implementation boundaries and remaining experiments.

## Engineering constraints

- Keep Hearthbound **Minecraft-first and fun-first**, with LLMs deferred while learning-based policies are validated. Keep exploratory society and benchmark modules isolated from production Forge behavior until gates pass.
- Model policies as complete observation/action/memory/learning configurations. Model star, tree, chain, graph, and optional learned network routing as communication **protocols** with explicit message delivery, budgets and topology changes.
- Separate intentions, commands accepted, agent testimony, and physically verified world changes. Only independent source/machine/output inventory witnesses establish task completion. Ensure durable provenance and no duplicated rewards/evidence.
- Keep independent personal, collective and research reward domains; separate completion, participation, social diversity, economic welfare and coordination costs in reporting.
- Never equate consensus with correctness, a leaderboard with equilibrium, a simulated society with human social validity, or scripted actions with learned emergence.
- Report every failed, incomplete, rejected, and invalid trial in denominators. Aggregate uncertainty over **independent worlds**, not citizens inside one colony. Freeze seeds, training budgets, models, policies, protocol contracts, version hashes and all scored inputs.
- When studying political or organizational emergence, infer organizations from observed exchanges, affiliations, elections and institutions; do not preset mandatory party identities, personalities or government outcomes. Political topic preferences must remain mutable and evidence/context-dependent, not inferred from real human demographics.
- Use matched controls: no messages, shuffled messages, static/flexible roles, memory on/off, trained/untrained/script, independent policy seeds and changed communication structures. Add full ordered profile tests when analyzing strategic deviations; cite uncertainty and uncovered strategies.
- Bind social evidence to world, sender, recipient, direct observation, delivery, selected report, policy and job. Preserve a pre-assignment snapshot. An inbox read is not use; an assigned job is not physical completion; an associated outcome is not a causal benefit. Never promote peer reports into direct observations or invent organizations from message counts.
- Preserve every prespecified independent-world trial, including infrastructure failures and missing artifacts. Diagnose the earlier 3-of-4 accounting failure from terminal physical/board evidence; successful repeats do not prove a fix. Keep pilot uncertainty and unknown outcomes visible.
- Test via standalone unit contracts, GitHub CI, actual Forge compilation and live physical acceptance **before** asserting an implemented runtime feature. Preserve existing Create/pickup/restart/conservation and four-citizen acceptance behavior. Do not silently merge stacked draft PRs.

## Relevant code and boundaries

- `experiments/marble-collaboration-bench.js`: pure scoped, verified-event milestone/communication scorer.
- `experiments/collaboration-evaluation-v0-2.js`: per-world provenance, matched-pair deltas and descriptive bootstrap estimates.
- `experiments/society-emergence.js`, `society-history.js`: standalone society hypotheses, not live Minecraft societal learning.
- `docs/PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md`: source distinctions, metrics and promotion gates.

A paper's stated benchmark result is **not** a Hearthbound result. Pin the actual upstream revision, especially because MARBLE's November 2026 maintenance changed benchmark runner behavior and repaired scenario data.
