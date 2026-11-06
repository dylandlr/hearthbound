# Hearthbound v0.15.6 — Real Forge/Create causal outcome probe

## Implemented

This release adds the permission-2 read-only operator command: /sable mill-outcome-probe <job-uuid>.

It joins three independently existing runtime records on the actual Forge server thread:

1. Sable's executor-assigned haul (villager persistent NBT, including newly recorded server-game-time assignment tick). This is not a learned model decision.
2. The MillProcessReceipts actual Create process() callback (world SavedData job, owner, machine, verified start/finish ticks and input/output state).
3. MillReservations.matches and exportVerified, which require a still-held, untainted job/citizen/machine reservation.

A valid result computes a deterministic physical evidence ID from the saved world UUID, dimension, machine location, job UUID, and exact Create start/finish ticks. It then invokes the existing OutcomeLedger with only the witnessed executor assignment as contributor and produces an illustrative personal proposal of 500 milli-points. Research and colony budgets are explicitly zero because no autonomous recipe discovery, independent research action or colony identity is evidenced.

No DurableRewardLedger.credit, research inbox enqueue, AI training, item transfer or technology unlock is performed.

## Fail-closed behavior

The probe denies missing Create callbacks, another citizen's job, unloaded machine chunks, missing/released/tainted mill reservations, invalid time ordering, missing legacy assignment ticks, incomplete hauling and mismatched assignment destination.

An identical probe returns the same physical event identifier and output but does not persist or pay anything. The in-memory OutcomeLedger is created and discarded per operator query; this is NOT cross-process durable replay protection.

## Actual Minecraft acceptance

The workflow .github/workflows/real-mill-outcome-probe.yml starts a fresh Forge/Create server and runs scripts/rcon_sable_first_mill.py against its actual RCON port.

The fixture must confirm:
- A real villager moves wheat from a chest to a powered Create millstone.
- The actual Create callback and physical flour production are observed.
- A provenance-bound read-only outcome is proposed and returns stable on replay.
- A nonexistent callback, another real villager claiming the same job, and a released mill reservation are all denied.
- Existing unauthorized direct-belt, external-item, taint and release regressions continue to pass.
- RCON and actual Forge server logs are uploaded for independent inspection.

This workflow must pass before v0.15.6 may be described as real Minecraft integration validated. Forge compilation and standalone unit checks alone do not establish that.

## Known limitations and next milestone

- Persistent villagers and SavedData are separate stores without a cross-store atomic transaction. A crash or job reassignment may remove the required assignment witness; the probe fails closed.
- Executor provenance is an operator-submitted task, not proof of self-motivated AI research.
- The presence of an authoritative process callback does not prove a research hypothesis was independently chosen.
- Reward admission, rollback reconciliation and late-taint checks remain disabled in live gameplay.
- Other contributor roles (farmer, research proposer, machine maintainer) need their own directly witnessed action receipts. Do not split a single Sable haul among imagined participants.
- The next acceptance should add durable process-to-assignment junction evidence across a real save/restart, including invalidation on taint and proof that no credit is ever paid in those denied cases. Afterwards add separately attributed social teaching events.

## Expected result

MILL_OUTCOME_PROPOSAL status=PROPOSED job=<uuid> citizen=<uuid> world=<uuid> ...
decision_origin=ACTUAL_EXECUTOR_ASSIGNMENT personal_milli=500 colony_milli=0 research_milli=0
reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT

This is a read-only audit and proposed engineered label, not an actual Minecraft reward.
