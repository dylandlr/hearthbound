# v0.9.3 — Read-only source-aware intent baseline

## Why this exists
The bundled MLP remains a five-feature **scripted imitation** model with no knowledge of source inventory. v0.9.2 established that the real server can distinguish a wheat chest that is empty, available, or not observable. v0.9.3 introduces a **separate scripted reference planner** that consumes this partial observation. It is intentionally neither a neural retraining nor a learned policy.

## Decision contract
The Java 17 pure reference planner evaluates real machine power, mill input/output, blockage, task activity, and source availability:

| State | Read-only reference intent |
|---|---|
| No power | `INSPECT_UNPOWERED` |
| Flour output or obstruction | `COLLECT_OUTPUT` |
| Wheat already processing or task active | `WAIT_FOR_PROCESSING` |
| Idle, source UNKNOWN | `INSPECT_SOURCE` |
| Idle, source EMPTY | `WAIT_FOR_SUPPLY` |
| Idle, source AVAILABLE | `REQUEST_WHEAT_HAUL` |

Only `REQUEST_WHEAT_HAUL` is a potential dispatch candidate; this planner has **no dispatch API**. Actual inventory and task authority remain in `SableHauling` and `MillPolicyTrial`. An UNKNOWN source is never conflated with EMPTY.

The command `/hearthbound policy_source_plan <source> <mill>` reads an actual Forge/Create millstone, the distance-limited source sensor and a marked Sable. It reports the intent, sensor reason, game tick, and `ML_MODEL_UNCHANGED EXECUTION_DISABLED`. Missing mill or ambiguous citizen identity fail closed.

## Acceptance
A pure Java test exhausts Boolean machine/task states x all three source states. The real Minecraft smoke test compares EMPTY -> WAIT_FOR_SUPPLY, UNKNOWN -> INSPECT_SOURCE, AVAILABLE -> REQUEST_WHEAT_HAUL and archives a strict `source-plans.json` report per policy arm. Existing successful hauling, shortage rejection, restart persistence and offline reward-accounting tests remain mandatory.

## Research restrictions
- The model's original 5-feature weights and hash are unchanged.
- The reference planner is a **new baseline** for a later 8+/feature observation schema.
- We have not established actual neural shortage avoidance or autonomous inspection/restocking.
- Next create a versioned observation tensor and train multiple policies on diverse states, with separate reference comparisons, held-out worlds and runtime feature parity.
