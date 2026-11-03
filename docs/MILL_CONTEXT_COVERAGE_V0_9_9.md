# Hearthbound v0.9.9 — Out-of-distribution real mill context coverage

## Prior verified result

The frozen simulator-trained neural Q policy matched the scripted reference on three distinct source states read from a previously successful real Forge/Create Minecraft run. The replay completed successfully, but the model did not act or learn in Minecraft.

The next task is to test **contexts absent from the simulator's three-action vocabulary**. A model that has learned where to find wheat still must not request a haul when a Create mill is unpowered, blocked, processing or awaiting collection.

## New actual-world observations

The dedicated-server harness records two additional states from genuine Create millstones:

- `unpowered`: the millstone exists, but no kinetic power is connected; the reference action is `INSPECT_UNPOWERED`.
- `output_ready`: a powered millstone has physically produced Create flour; the reference action is `COLLECT_OUTPUT`.

Each `REAL_MILL_CONTEXT` receipt includes the exact ten-feature `hearthbound.mill-observation.v2` tensor. Both must be read-only. Existing actual Minecraft source states, two policy arms, flour production, persisted Sable memory, and reward ledger checks remain in place.

## Neural action applicability gate

The simulator Q model has only `INSPECT_SOURCE`, `WAIT_FOR_SUPPLY`, and `REQUEST_WHEAT_HAUL`. For unpowered, obstructed, busy, processing, output-ready, or stale source conditions, these actions may be inappropriate. The new `NeuralQContextGate` fails closed with `ABSTAIN`; it also rejects source-state/action mismatches.

The gate **does not grant permission to dispatch**, even for a valid `REQUEST_WHEAT_HAUL` prediction. Actual task authority remains in Minecraft's existing validated controllers. A pure Java regression test exhaustively checks the action/state matrix. An independent Java runner reads both real Minecraft RCON logs after the successful server tests, applies the frozen neural Q network, and asserts that unsupported states **always abstain**. A strict two-arm artifact reports the two distinct world states and never infers autonomous learning.

## Limits and acceptance

This milestone requires full actual-world validation and does not assume that previously green logs contain these new contexts. Forge compilation/JAR/download CI has recently failed due to third-party Maven certificate errors; fast Java parity and contract tests can pass independently.

We still need time-sequenced, genuinely held-out, multi-seed Minecraft episodes and real consequences of alternative task choices before comparing return or promoting neural execution. The three-action model remains simulator-only and read-only.
