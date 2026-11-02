# v0.8.1 — Sequential colony outcome benchmark

The initial v0.8.0 CI run passed, but one-step scripted-label accuracy is not an outcome metric. This experiment compares a scripted baseline, the identical-weights untrained MLP, and an imitation-trained MLP on **paired 60-step simulated episodes**.

The closed-loop surrogate tracks hunger, fatigue, wheat inventory, mill power, threat, travel, produced flour, wasted actions and unsafe decisions. Identical episode seeds and transition sequences make the policies comparable; decisions still change observed outcomes. The scripts include deterministic transition tests.

```bash
python experiments/first-mlp/test_sequential_rollout.py
python experiments/first-mlp/sequential_rollout.py --episodes 300 --steps 60
```

**Limitations:** This is a simplistic synthetic task abstraction, not the actual Minecraft server, Create machinery, fast colony simulator, RL training, or a realistic partially observable multi-agent colony. The imitation MLP is still trained from scripted labels. A model may have high imitation accuracy and poor episode performance; report both without altering reward criteria. CI outcome pending.

**Next:** Add logged policy action inference to the Minecraft server, use the same observation schema without privileged features, run an A/B policy comparison on equivalent live Minecraft layouts, then train a reward-driven agent using a proper rollout environment.
