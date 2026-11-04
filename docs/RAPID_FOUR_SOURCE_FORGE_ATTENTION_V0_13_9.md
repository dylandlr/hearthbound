# Hearthbound v0.13.9 — Rapid four-source real Forge attention challenge

## Why

The previously verified Forge experiments (PRs #157–159) repeatedly reached **6 of 6** witnessed interventions under two watched chests. Across three configured seeds the scripted selector was faster (mean first witness latency ~4.67 ticks versus ~7.28 neural ticks). This establishes no neural advantage and suggests that fair rotation is especially well suited to a two-source fixture with forgiving resource timings.

This milestone creates a separate high-contention experimental fixture without changing or reinterpreting the original nine-server baseline.

## Four-source environment and treatment

Add **two additional disposable real Minecraft Forge servers**, producing eleven server jobs total:

| Arm | Attention policy during new challenge | Configured seed |
|---|---|---|
| SCRIPTED-D | LEAST_RECENTLY_SAMPLED | `hearthbound-rapid-four-D` |
| NEURAL-D | NEURAL_CAUSAL_MLP_OPT_IN | `hearthbound-rapid-four-D` |

Both servers first pass the exact existing scripted Forge, RCON, observation, privacy, finalized journal and restart regression. **After** those baseline checks, a separate citizen attention journal begins. The operator rebuilds four actual Minecraft chests at (7,100,2), (8,100,2), (9,100,2), and (10,100,2), moves marked citizen Sable nearby, and registers all four as read-only candidate watches. They remain the only candidate sources. Neural activation is explicitly opt-in and starts only after four-source registration; the server's one-inspection-per-five-ticks per-citizen gate remains unchanged.

The challenge plan generates **16 seeded, deterministic, nonuniformly distributed resource mutations**, more frequent at source (7,100,2), with 0.11-second nominal pauses. These operator-issued `data merge block` commands modify real chest NBT. All required commands receive actual RCON responses and server game-tick timestamps, and the run records a pre-cleanup cutoff tick. The fixed plan and every verified execution receipt are archived. The operator cannot infer that any resource was perceived merely because a mutation succeeded.

## Outcome measures

A separate finalized Forge citizen journal records which single registered source each policy selected, and the selected source's real observation only. The auditor discards watch-setup and cleanup events, rejects any non-four-source candidate set or policy contamination inside the challenge window, and uses the server's real tick boundaries to compute:

- Total selected-source inspections in the challenge.
- Number of 16 resource-state changes actually witnessed within their own valid same-source window.
- Unwitnessed changes, which remain unknown to the citizen.
- Direct inspection count and first-witness latency per intervention.

The comparison checks both runs' plan digests, configured seed, resource values/source sequence, distinct finalized run IDs, bounded counters, and report hashes. It publishes a **descriptive** scripted/neural witness-count difference and does not claim identical server-tick stimulus timing, a causal treatment effect, a neural advantage, or generalization to independent worlds.

## Scientific caveats

A 0.11-second host pause is **not** a guaranteed number of Minecraft ticks. RCON latency and server tick rate vary between runs; matching plan hashes guarantee command order and intended resource counts, not identical tick-aligned stimulus histories. The event windows explicitly exclude ambiguous same-tick observations. The generated chests and changes are operator authored, not natural ecology; our learned neural model remains simulator trained. No LLMs, navigation, hauling, crafting or new task authority is enabled.

A meaningful causal comparison would later require tick-triggered server-authoritative interventions, balanced replication, held-out fixture patterns and a pre-registered evaluation protocol.

## Acceptance

1. Existing nine server trials and their comparisons remain fully green.
2. Both new real Forge challenge arms must complete 16 RCON-confirmed mutations, finalize a separate four-source journal and emit valid observation coverage.
3. The NEURAL arm must provide actual neural-tagged inspection decisions during the challenge; no offline recommendations or post-run-only canaries count.
4. The scripted arm must remain on the original policy; neither arm may increase the one-inspection-per-five-ticks budget.
5. `compare-rapid-four-attention` must produce a verified matched real-Forge report with clearly qualified descriptive metrics.

No performance results should be claimed before the new dedicated-server CI run and artifacts are verified.
