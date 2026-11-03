# Hearthbound v0.10.6 — Observation-age-aware option selection

## Hypothesis

The frozen v0.10.5 learned high-level controller completed many synthetic tasks under delayed sensors, but required numerous interventions from the separate current-state safety supervisor. We must distinguish **success after intervention** from **the rate of legally executable proposals**, rather than treating supervisor intervention as autonomous competence.

## New learning setup

The previous `19→24→3` meta-controller stays frozen as the baseline. A distinct `21→24→4` neural Q controller trains high-level options SEEK_WHEAT, SECONDARY_JOB, WAIT, and REFRESH_SENSORS. Its 21 inputs contain the existing 15 bounded task/source features, a four-way previous-option indicator, one remembered secondary-completion event, and a bounded observation-age feature. No hidden resource contents are supplied.

REFRESH_SENSORS is a **simulator-only** abstract action, not a real Minecraft command. It advances the simulator one full WAIT transition, then obtains a fresh post-step observation **for the next decision**, without disclosing the result to the prior decision or skipping world time. No action can bypass the independent current-state safety supervisor. It substitutes WAIT for unsafe proposed primitives.

To avoid overstating realism, the training environment uses the same five profile parameterizations (0-, 2-, 3-, 4-step sensor latency and periodic interruptions) as the evaluation stress suite but disjoint training and held-out episode seeds. This is **held-out episode evaluation**, not held-out delay-profile transfer. The controller learns via TD reward with separate original personal and colony rewards, and a small training penalty for supervisor-rejected stale proposals.

## Comparators and metrics

For each independent network training seed 11,13,17, the experiment reproduces the original frozen low-level goal-bonus Q network and v0.10.4 high-level learned option Q network. It trains the new age-aware policy only on newly generated simulator episodes. Evaluate both age-aware and legacy policies on the same five stress profiles × five source regimes × 30 independent held-out seeds per cell.

Separate metrics:
- Flour completion and separate personal/colony reward per simulated episode.
- Total safety-supervisor rejections, including those due to stale proposals.
- Unintervened valid-action proposal rate (rejects divided by non-interrupted decisions).
- Sensor refresh requests, forced interruptions, mean steps, and invalid executed requests.
- Per-scenario recorded event traces and immutable model hashes.

The principal acceptance check is whether the age-aware policy **reduces unsafe proposals while preserving task completion**. A successful CI run only proves reproducibility and contract validity, not an improved policy. Any outcome, including worse performance or excessive refreshing, must be recorded. All behaviors are SIMULATED_ONLY and do not authorize new Minecraft commands, neural task dispatch, or an online learning loop.

## Engineering limits

The sensory transport delay and resource dynamics remain abstract and may not correspond to real Minecraft chunk updates. A separate supervisor is still present, and independent action authorization would require real observation freshness, inventory confirmation, claim ownership and gameplay rollback testing. No LLMs are involved. A network with one explicit age feature is not a recurrent network.

The v0.10.5 PR succeeded in simulator stress tests; its Forge integration is a separate check. This experiment changes none of the live game-controller code.
