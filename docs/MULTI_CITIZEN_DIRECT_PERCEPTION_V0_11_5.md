# Hearthbound v0.11.5 — Individual citizen direct-source perception

Experimental stack on PR #135. This step extends the already verified per-citizen NBT memory without allowing any neural controller to act. It is an operator-triggered proof that marked non-Sable citizens can make independent physically bounded observations.

## Design decisions

- Each marked villager (legacy `hearthbound.sable` or generic `hearthbound.citizen`) can own direct knowledge in its own Forge persistent NBT.
- `/hearthbound citizen_observe <source> <observer>` performs **one** live read through the existing `SourceWheatObservation.inspect` with chunk-load, dimension, physical range and supported-inventory checks. No global scan, no automatic access to a watched source, and no task execution.
- `/hearthbound citizen_memory <source> <citizen>` reads that specific citizen's direct knowledge without opening the current inventory or including received reports.
- Reported knowledge continues to be retained by `CitizenKnowledgeExchange` separately from direct evidence.
- This slice deliberately does not extend the automatic watch's Sable-specific selection. Future automatic multi-citizen sampling needs a bounded per-citizen watch registry and independent dedup/revision per observer, otherwise one citizen could suppress another citizen's receipt.
- Operator-only commands require permission level 2 and never authorize inventory work.

## Live Forge acceptance

The existing dedicated-server test now additionally uses a second real chest at (9,100,2) and the already summoned, individually marked recipient. It asserts:
1. Neither Sable nor the recipient initially knows the second source.
2. A physical RCON mutation adds three wheat.
3. A direct recipient observation returns AVAILABLE / 3 wheat and `action_authorized=false`.
4. Only the recipient's direct memory becomes KNOWN (3 wheat); Sable remains UNKNOWN about that source.
5. A report previously sent from Sable about the first source is **not** promoted to the recipient's direct memory.
6. Both scripted and trained-MLP Forge trial arms retain their existing acceptance and restart contracts.

Do not claim real-server acceptance until this branch's workflow is green.

## Next step

Implement a bounded per-citizen watch registry (not a global 16-block omniscient broadcast), run two simultaneous source observations, and compare isolated versus communicating colony baselines with equal access to the same physical environment. Require independent, server-validated action gating in every condition.
