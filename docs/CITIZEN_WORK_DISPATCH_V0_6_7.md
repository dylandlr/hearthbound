# Hearthbound v0.6.7 — Shared decision dispatch contract

`CitizenWorkDispatcher` binds the existing ColonyPolicy and ActionGate
to exclusive CitizenTaskArbiter leases and a world-owned Executor callback.
It logs accepted/rejected choices for replay and debugging. Dispatch must be
invoked at a *decision boundary* only; a running task retains its lease.
Rejections, stale observations and unsupported actions never change Minecraft.
A declined executor releases its tentative lease.

## Supported ownership mappings
- STUDY -> STUDY
- HAUL/DELIVER -> HAUL
- OPERATE -> EXPERIMENT
- REST -> REST

FLEE, EAT, FOLLOW and IDLE still require dedicated transition semantics.
Emergency cancellation/preemption is **not** implemented here: server safety
systems must explicitly handle those situations.

## Critical integration limitations
This pure Java contract does not yet replace existing world-side hauling
reservations or library task NBT. A real server bridge must own a common
arbiter instance, persist or reconstruct lease identity, choose complete
executable candidates, and guarantee that both hauling and studying call
complete/release. Do not put an unvalidated physical task in the observation.
Do not run dispatcher plus the autonomous library tick as competing schedulers.

## Regression gates
- Only one active lease per citizen
- ActionGate rejects stale proposals
- Declined physical assignment relinquishes tentative lease
- Stale completion cannot release a newer lease
- Unsupported actions do not acquire ownership
- Accepted and rejected decisions are traced

The policy and contracts are compatible with Java 17; no Minecraft runtime
verification or successful CI run is claimed here.
