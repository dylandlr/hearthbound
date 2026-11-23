# Verified four-citizen task participation v0.7 (MARBLE-inspired)

This research slice follows **MultiAgentBench / MARBLE** (ACL 2025) and the user's PA4 reading review (especially P42/P06/P32/P33). It adapts the distinction between **milestone completion** and **credited participation** to the real physical hauling evidence established by #205–#208.

## Observed physical milestone basis

The `scripts/export-four-citizen-benchmark.js` gate already requires a successful real four-citizen Forge RCON run with four emptied sources, four wheat at destination, zero claims, exact scoped four-citizen history and physical decision/job trace joins. Its output version `hearthbound.collaboration_evidence.v0.4` contains four separate verified completed haul task records, each with exactly one distinct citizen, job, decision and evidence UUID. This slice adds `fixtureParticipation` computed from that verified output by `scripts/score-verified-citizen-participation.js`.

The scorer **does not** accept a naked event log: it expects the *already validated* exporter result, checks its acceptance attestation, real fixture identity, CI run/commit/log digest fields, physical counts, unique trace identities, evidence age and chronology.

## Correct denominators

For this specific fixture only:
- Agents N=4
- Independently completed physical haul tasks / milestone count M=4
- One directly credited citizen for each physical haul: sum(n_j)=4
- Verified task completion = 4/4 = 1.0
- MARBLE-style average participation KPI = sum(n_j)/(N*M) = 4/(4*4) = **0.25**
- Every citizen participated in at least one of the fixture's verified task milestones: **4/4 citizens**.

A KPI of 0.25 is **not** evidence that 75% of work was missed, nor evidence that society collaboration was weak. In single-executor tasks the KPI declines with N even if every milestone is complete. The distinction is exactly the measurement pitfall flagged in the PA4 P42 review.

The JSON output retains `scores.individualParticipation=null` for the **general cross-scenario participation claim** and adds a separately namespaced `fixtureParticipation.metrics.marbleStyleParticipationKpi` tied only to these four physically witnessed jobs. It must not be pooled with entirely different milestones, population sizes, or MARBLE's LLM-judge scores without a compatible shared benchmark contract.

## What is *not* measured

The RCON case contains **no recorded inter-citizen messages, no comparison topology, no learned policy promotion, no emergence of professions or organizations, no independent world-seed replications**, and no newly added game control. For those categories the fixture scorer returns `null`, not zero and not made-up credits. A successful four-delivery trial cannot establish the earlier intermittent queue/accounting failure was fixed.

Evidence authenticity still depends on the actual GitHub-hosted Forge run and original physical checks; a SHA-256 of a submitted text log by itself does not authenticate it. Each future experiment must bind the identical metric to comparable tasks and evidence scopes before estimating a treatment effect.

## Tests

```bash
node scripts/score-verified-citizen-participation.test.js
node scripts/export-four-citizen-benchmark.test.js
```

The real four-citizen workflow now triggers on scorer/exporter changes, checks both suites, and produces the same independently verified JSON artifact with the new scoped score. Keep live acceptance thresholds unchanged. Require completed exact-head Forge CI before claiming any real v0.7 export.

## Next milestone

Add real sent/delivered/read communication evidence, explicitly document which peers can receive each observation, and train/compare policy variants on matched independently seeded worlds. Do **not** assign teamwork credit from shared intent, inferred closeness, or messages alone.
