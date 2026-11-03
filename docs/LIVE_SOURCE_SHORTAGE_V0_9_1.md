# v0.9.1 — Real Minecraft source-shortage refusal

The first negative outcome experiment runs **inside the actual Forge/Create dedicated server** for both SCRIPTED and TRAINED_MLP modes. Before each successful one-shot haul, the fixture now places an empty chest at the intended wheat source and invokes the policy trial.

Acceptance requires the live command to reject with `Source inventory has no real wheat`, a read-only Sable audit to confirm her prior job remains complete, and a distinct `REAL_POLICY_TRIAL_REJECTION` log record. Only after refusal does the harness restore one wheat, rerun policy selection, and verify flour production, citizen experience, and server-restart persistence.

The new `policy-rejection.json` artifact records zero colony and personal task rewards, and `training_transition=false`. A refusal is **not** treated as a completed RL episode or artificially labeled a neural success/failure. The existing reward-ledger for the later successful task remains separate.

## Architecture finding

The current 5-feature MLP sees Create power, machine wheat/flour, obstruction and citizen experience, **but not source inventory availability**. Thus it may recommend `REQUEST_WHEAT_HAUL` even when the source is empty. The authoritative `MillPolicyTrial` gate correctly rejects such an attempt. This distinction is important: safety enforcement is working, but the policy lacks an observation necessary for learning an effective choice between work, waiting and resource acquisition.

Next agent observation schema should add source-known/source-wheat-present, citizen task/busy state, destination ownership, available fuel/energy and stale-observation flags, with explicit validity masks. Actual world observations should be partial and time-stamped. Repeated held-out scenarios are required before RL training. Do not infer universal safety or model superiority from this single refusal.

This milestone tests real refusal behavior but does not autonomously replan a successful recovery; manually supplying wheat in CI is a fixture reset, not Sable discovering a resource.
