# Hearthbound v2.8 — Minecraft decision boundary instrumentation

On opt-in autonomous research consideration (after the eligibility/cooldown checks and finding a local experiment site), the runtime evaluates SCRIPTED and PERSONALITY against the same grounded local observation and writes one bounded trace per citizen/tick.

## Path

1. `AutonomousMillResearch.tick` reaches a physical experiment site.
2. `LocalMillExperimentSensor.observe` checks loaded chunks, distance, wheat, real Create millstone, and existing hypothesis; invalid contexts return null.
3. `ResearchDecisionRuntime.capture` compares policies through `ResearchDecisionComparison.evaluate` and records in the versioned `ResearchDecisionTraceJournal`.
4. Original `LocalMillExperimentSensor.consider` retains action selection under PERSONALITY mode. The recording path does not issue actions, claim resources, propose hypotheses, or mint evidence.

## Current guarantees and limitations

- Server-only in-memory telemetry (256 traces per citizen, order enforced by game tick).
- Existing research behavior unchanged except diagnostic sampling overhead and refactoring the sensor.
- Actual decision-boundary capture, not synthetic benchmarks.
- Exports are read-only via Java `ResearchDecisionRuntime.exportJson()`, **not yet available as an operator command**.
- No across-restart journal persistence, no verified Create receipts attached to decision traces, and no dashboard feed.
- Tick ordering is strict, so repeated capture on the same game tick will reject; caller currently invokes once per actual consideration. Integration regression should verify this assumption.
- Requires Forge CI compilation and Minecraft integration checks before merging.

## Follow-up acceptance tests

- Forge server compiles and independent research/haul workflows still pass.
- Loaded mill + wheat produces one decision trace during consideration.
- Unloaded chunk, distant machine, no wheat, or known hypothesis yields no trace.
- Trace exports do not change research knowledge, claims, inventory, or rewards.
- Restart semantics are explicitly tested before adding persistence.
