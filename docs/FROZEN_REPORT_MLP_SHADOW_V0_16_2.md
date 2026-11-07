# Hearthbound v0.16.2 — Frozen report-conditioned MLP (shadow only)

## Research goal

Replace the explicit scripted `highest reported wheat` selector from v0.16.1 with a genuinely trained but **frozen** neural model. Compare both on the **same recipient-owned citizen reports, same source menu and same real Forge world**, using report exposure versus withholding.

The MLP is trained on simulated source reports and sampled **synthetic** pickup outcomes. This is supervised one-step outcome regression with a sampled hidden simulator label for each source, **not** online RL, real Minecraft experience replay, or a trained collaboration mechanism. The evaluated action remains a read-only source choice: it never schedules a haul.

## Model and features

Version: `hearthbound.report-choice-mlp.v1`

Architecture: two-layer MLP, `10 → 16 tanh → 3 linear`, outputs `SOURCE_A, SOURCE_B, ABSTAIN`.

Each of the two candidate sources has exactly five input features:

1. A recipient-visible, delivered report presence bit.
2. Previously reported wheat normalized to 0–1.
3. Age since report delivery normalized by 200 ticks.
4. Age since direct observation normalized by 240 ticks.
5. The report revision (capped at 16) normalized by 16.

**Never present** in network input: actual current wheat or block inventories, unexplored chunks, source UUID/world seed, hidden simulator pickup result, machine output, executor outcome, or future state. The exposure arm chooses which recipient-owned report NBT is allowed into the feature encoder. The withheld arm never accesses those NBT entries. A hard action mask prohibits selecting a source without an admissible report even when model scores are erroneously optimistic.

## Training protocol

`scripts/train_report_choice_mlp.py` uses only Python's standard library, seeded synthetic resource reports and hidden stochastic pickup outcomes. It trains all three output regressions with gradient descent. The simulator, not Forge, provides the synthetic labels, including possible outcomes for both alternative choices; no counterfactual real-Minecraft delivery is inferred.

Default training seed: `20261107`; held-out synthetic evaluation seed: `20361107`; 18,000 synthetic examples, five epochs, 1,600 held-out paired evaluation examples.

The generated `run/report-choice-mlp-v1.txt` and `run/report-choice-mlp-v1.sha256` are finalized **before** starting Forge. CI trains a second time and requires exact byte-for-byte agreement and the same SHA-256. Java loads the file only once, checks the full SHA manifest, requires explicit simulator-only provenance and fixed tensor dimensions, and never updates weights.

The held-out evaluation reports simulated mean reward, selection rate, synthetic successful pickup rate and disagreement with the simple scripted baseline. No unsupported Minecraft success metrics are claimed.

## Real Minecraft read-only experiment

New permission-2 command:

```text
/hearthbound-report-mlp-choice <recipient> <source-a> <source-b> <exposed|withheld>
```

Same real `CitizenKnowledgeExchange.decisionReport` accessor and source keys as the v0.16.1 scripted policy. The new policy reads **only** previously delivered recipient NBT. No live `SourceWheatObservation.inspect` or inventory API. If the frozen weights are absent, corrupted or have incompatible provenance, the operator probe fails closed rather than falling back silently to scripted choices.

`.github/workflows/real-frozen-report-mlp.yml` trains and hashes the model before Forge starts, then executes `scripts/rcon_report_choice_experiment.py` with `HEARTHBOUND_REPORT_MLP=1`.

Expected physical-world observations:

- Withheld reports: both policies abstain.
- Fresh direct reports for A=3 wheat, B=1 wheat: exposed scripted and exposed frozen MLP should choose A.
- An uncommunicated operator chest-A mutation to empty: both must keep choosing A from their *stale report*, showing absence of omniscient inventory input.
- When the sender directly observes empty A and communicates the new report: both should select B. The earlier A observation is superseded.
- The actual real-world test does not execute either policy's suggested hauling action. It therefore does **not** measure real pickup success, learned teamwork, or contribution shares.

## Next acceptance gate

After the read-only shadow passes, perform matched, seed-controlled *physical* hauling trials with a real executor. Only pre-bound, executable tasks may be chosen; attribution must come from current inventory deltas and the authoritative server callback. Measure paired difference in successful deliveries, time to completion, abstention quality, and per-seed confidence intervals before any claim of improvement.

One unresolved safety issue remains [#181](https://github.com/dylandlr/hearthbound/issues/181): intermittent navigation below target elevation. Hold the physical trial design to the existing delivery requirements; do not count an unexecuted neural choice as success or weaken the test threshold.

**Rewards, research-inbox writes, citizen training, social reputation changes, and Create technology unlocks remain disabled** in this milestone. LLMs remain out of scope.
