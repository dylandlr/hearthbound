# Agent architecture v0.2

This slice turns the societal-emergence plan into an executable, Minecraft-independent contract. It deliberately starts with the Homestead milling benchmark and leaves personality, genomes, relationships, reproduction, communication, recreation, and research discovery for later vertical slices.

## Contract

- `MillState` is authoritative simulator state.
- `MillObservation` is a partially observable policy view. Hidden quantities are zero-filled and paired with visibility features, so “unknown” is distinct from a visible zero.
- `HierarchicalTask` exposes four task-level actions: wait, supply the mill, collect flour, and return to the waiting/store area.
- `MillObservationEncoder` publishes a stable, ordered, bounded 20-feature vector for MLP policies.
- `RewardFrame` keeps named personal and colony reward components separate.
- `DeterministicMillSimulator` validates every action, preserves inventory, and supports replay from an initial state, action sequence, and seed.
- `ScriptedMillPolicyV02` is the first baseline. Learned MLP policies implement the same `AgentPolicyV02` interface.

The seed is already part of the replay contract even though v0.2 transitions contain no randomness.

## Reward contract

Reward values are benchmark mechanics, not claims about human or societal motivation.

| Event | Personal | Colony |
| --- | ---: | ---: |
| Useful supply | +0.02 | 0 |
| Useful collection | +0.02 | 0 |
| Completed delivery | +0.03 per flour | +1.0 per flour |
| First target completion | 0 | +2.0 |
| Valid wait | -0.001 | 0 |
| Rejected action | -0.25 | 0 |

Rejected actions are atomic: state and simulator step do not change.

## Acceptance boundary

The dependency-free acceptance suite verifies schema order and bounds, hidden-state non-leakage, deterministic replay, atomic rejection, split reward provenance, conservation, and successful scripted completion. Run it with `./scripts/test-core.sh`.

## Next slices

1. Connect the observation/action adapter to Minecraft’s workshop state.
2. Add dataset recording and scripted/tree/forest comparisons.
3. Train an MLP against the same fixed schema and action mask.
4. Add evidence-ledger and research-discovery contracts.
5. Introduce personality and relationships only after task learning has measurable baselines.
