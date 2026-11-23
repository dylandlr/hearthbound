# Colony source readiness and participation diagnostics v0.9

**Scope: read-only diagnosis, not a gameplay or fairness fix.** This branch follows the successful real Forge citizen communication test and the unsuccessful first five-world reliability pilot on commit `01b45f5e931b1e39e9a25469d2f7577105c939c7`.

## Observed reliability problems

The predeclared pilot (five worlds) had two full passes, two gameplay failures, and one dependency preflight failure. World-01 reached the full observation deadline with a wheat source unconsumed, `done=3 assigned=0`; world-02 completed four physical jobs but counted only three distinct workers. These are different from the prior physical four/queue three assigned one accounting anomaly. That earlier defect remains open.

The dispatcher permits a citizen who finishes a job to compete for another queued task. This explains *how* four tasks can be completed by only three citizens, but does not establish which exact scheduling decisions produced world-02's outcome. World-01's missing source needs citizen position and local observation reach recorded at the time of failure. Do not introduce a universal one-job-per-citizen cap: it would artificially restrict future employment, specialization and production.

## New read-only Minecraft command

```
hearthbound-colony source-readiness-audit <x> <y> <z>
```

This operator-only audit examines one explicitly requested loaded source, looking at currently loaded marked villagers within 16 blocks. It returns sorted, bounded per-citizen evidence: UUID, current integer block position, squared distance, whether the source falls within the autonomous local 2×1×2 source scan and 16-block job menu, whether a motor is active, and numbers of DONE/ASSIGNED/HELD or reserved jobs. It does not sample unknown unloaded citizens, move NPCs, claim inventory, change AI policy or authorize rewards. It reports truncation if over 16 citizens are locally visible.

The pre-existing four-citizen RCON acceptance collects this at intermediate polls and at terminal incomplete-work failures. This allows distinguishing physical disappearance of a work opportunity, an agent moving out of scanner reach, duplicate worker participation, and an unresolved assignment. These are still snapshots, not proof of what the citizen observed on earlier ticks.

## Separate offline result categories

`scripts/summarize_colony_reliability.py` now emits independent `terminal_diagnostic_patterns` and per-trial `diagnostic_flags` when their read-only terminal witness is valid:

- `PHYSICAL_FOUR_TASK_THREE_ASSIGNED_ONE`: original stable four-physical/board-three-assigned-one signature.
- `FOUR_DELIVERIES_FEWER_THAN_FOUR_CITIZENS`: four physically completed and accounted tasks with fewer than four distinct contributors.
- `SOURCE_REMAINS_NO_ASSIGNED_TASK`: incomplete physical inventory and fewer than four completed tasks, with no queued assignment remaining.

These labels **do not alter** the preregistered `status`, the complete-world denominator, Wilson uncertainty or unknown classification. No missing or invalid artifact is silently promoted to a successful world. The original five-world cohort remains archived at its prior commit and protocol; new CI is another cohort at a new revision and must not be pooled naively.

## Research basis

- Project Sid: distinguish agents' intended actions, world outcomes, and module boundaries without claiming LLM-driven simulated sociology has been reproduced.
- MultiAgentBench/MARBLE: independent physical completion versus distinct worker contribution; do not confound task throughput with individual participation.
- PA4: MAST for evidence-based failure labels; ReAct for observation/action/outcome chronology; EGTA for comparison scope and missing-data limitations.

**Promotion criteria:** pass Java/Python contracts, Forge compilation, the existing four-citizen physical acceptance, and at least one new diagnostic failure artifact; then use the observed cause to design a targeted allocator/motor change with matched independent-world controls. This PR does not claim resolved reliability, MARL coordination benefit, or emergent professions.
