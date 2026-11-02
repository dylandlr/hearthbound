# v0.8.0 — First policy-learning baseline

This benchmark evaluates a **supervised imitation** MLP on synthetic, partially observable colony task-selection scenarios. This is an initial sanity check, not reinforcement learning or empirical Minecraft citizen improvement.

Six observed features: hunger, fatigue, wheat held, mill powered, threat, travel. Five high-level actions: eat, rest, collect wheat, mill wheat, wait. The scripted baseline supplies labels, so its 100% score is tautological. The random MLP and trained MLP start with identical weights. Train and held-out scenario RNG seeds differ; held-out threat and travel distributions are shifted.

Run with Python 3, numpy, torch:
```bash
pip install numpy torch
python experiments/first-mlp/policy_experiment.py --output policy-results.json
```

On the reference local run with seed 20261102, 12,000 training scenarios, 3,000 held-out scenarios and 35 epochs: untrained MLP 36.67% / 240 safety violations; trained MLP 93.43% / 19 safety violations; scripted oracle 100% / zero. Metrics use a one-step proxy, **not** actual flour output, Minecraft ticks, or learned behavior after world experience.

Next essential steps:
1. Add a *non-oracle* heuristic baseline, multiple seeds, confidence intervals and ablations.
2. Integrate observations/action masks into Hearthbound's fast simulator.
3. Record trajectories and improve a policy through real reward-driven experience (RL), not only imitation.
4. Export a versioned inference artifact compatible with the Java agent and test on held-out real Minecraft layouts.
5. Compare scripted, untrained, imitation, and RL policies on real task completion, ticks, waste and safety without privileged observations.
