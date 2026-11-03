# v0.8.9 — Initial two-arm real Minecraft task comparison

**Question**: Can both scripted and imitation-trained MLP select a real wheat-hauling task that Sable completes using the same authoritative task executor?

The dedicated Forge server workflow now uses a two-item GitHub Actions matrix: `SCRIPTED` and `TRAINED_MLP`. Each job starts a separate disposable Minecraft world, prepares the same flat test fixture and Create mill, and invokes:
```
/hearthbound policy_trial 8 100 1 9 100 3 SCRIPTED
/hearthbound policy_trial 8 100 1 9 100 3 TRAINED_MLP
```
Only the configured arm runs in each world. The dedicated RCON test validates an authorized task, real wheat transfer, observed Create flour production, citizen experience=1, and a separate complete save/restart memory check. It captures Minecraft `time query gametime` before and after the one-shot task and reports `REAL_POLICY_TRIAL_RESULT` with elapsed ticks. The strict `scripts/report_policy_trial.py` parser writes `policy-trial-result.json` only when the required evidence markers and valid durations are present.

Separate job artifacts preserve `minecraft-policy-trial-SCRIPTED` and `minecraft-policy-trial-TRAINED_MLP`, each including the RCON transcript and structured trial JSON.

## Interpretation rules

- These are two fresh worlds with matched **fixture geometry and supplies**, **not** exact RNG-matched trajectories. Minecraft mob AI, initial game time and server scheduling can vary between independent runs.
- One episode per arm is only a smoke comparison; no claims of superiority, statistical significance, improved intelligence or reinforcement learning are warranted.
- Both arms use the same executable task controller and action mask. The trained MLP imitates the scripted rule and does not train on Minecraft feedback yet.
- Only the hauling request is policy-selected. Navigation, transfer, recipe processing and experience bookkeeping are unchanged.
- A reliable A/B requires multiple independent seeds/replicates, frozen model hashes, the same fixed starting citizen attributes and strictly paired gameplay tasks with metrics such as completion, flour, elapsed ticks, waste and safety. We must also address effect of prior chest-hauling warmup and citizen state.
- The supervised rule-derived labels are privileged by the simulator. Comparing to a robust non-oracle heuristic and eventually reward-trained policies is required.

A successful CI run is a **proof of actual Minecraft task dispatch** for the two policies, not evidence that the neural policy outperforms scripted rules.
