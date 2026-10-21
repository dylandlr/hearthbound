# Hearthbound v2.9 — Verified training-transition assembler

Introduces `VerifiedTrainingTransitions` for connecting a policy's **executed proposal** to the real physical job UUID and, later, a verified `MillResearchRewards.Award`.

It deliberately does not treat a policy comparison, successful proposal, or projected utility as an actual reward. Bindings must be registered after the game successfully admits a physical job. Only `MillResearchRewards.awardVerified` results can be supplied by the trusted integration path. A job, citizen, decision tick and evidence ID must agree.

Training record schema v1: job UUID, citizen UUID, decision tick, outcome tick, actual action, recipe ID, evidence ID, and distinct personal/colony/research reward values. Records are immutable snapshots.

Guards: rejected counterfactual DEFER, mismatched citizen, future decision, missing binding, duplicate job, and duplicate evidence.

**Not yet an end-to-end trainer.** No job UUID is currently wired from `SableHauling.assign` to this assembler, the output is in memory, there is no durable replay buffer, and no next-observation or terminal flags; therefore this is an attributable reward record, not a complete TD/RL (s,a,r,s') transition. Next: physically-grounded binding at dispatch, verified receipt callback, persist/replay and add successor observation, then train offline baselines. CI verification required.
