# Hearthbound v3.0 — Physical job to verified learning award bridge

## Implemented
- On successful autonomous mill haul admission, link the **same-tick**, actually selected PERSONALITY PROPOSE trace to the assigned SableHauling job UUID.
- On the server-authoritative MillResearchRewards.awardVerified completion, finalize the link into a schema-v1 training reward record.
- Missing traces, mismatched citizens, duplicate jobs/evidence, and future decisions are rejected by the v2.9 attribution contract.
- Telemetry is optional and diagnostic failures are logged without invalidating a physical hauling job or research reward.

## Important limitations
- These are (decision, actual action, verified reward) records, **not** full RL transitions: no encoded state, next state, done flag, or advantage calculation.
- Record buffers and job bindings remain process-local. Restarts may cause the reward journal to succeed while optional attribution cannot be reconstructed; the bridge fails closed.
- Not all research actions flow through this code path.
- No model training, persistence, dashboard integration, export command or UI has been completed.
- Live Forge compilation and end-to-end Minecraft regression results must be checked before merging.

## Next acceptance gates
1. Spawn opt-in autonomous citizen with a loaded physical wheat source + powered Create mill; record one same-tick proposal bound to the hauling job ID.
2. Complete real machine processing and verify reward journal contains exactly one award; training record includes that verified evidence ID and matching job/citizen.
3. Failed, quarantined, cancelled or tainted jobs must produce zero finalized training records.
4. Repeat completion callback and restart at key phases to verify duplicate suppression and fail-closed attribution.
5. Add explicit successor observation and crash-safe dataset storage before offline MLP experiments.
