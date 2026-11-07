# Hearthbound v0.16.0 — Direct Source Witness Before Milling

## Motivation

The colony now has two separately embodied roles in a real Forge/Create task:

- **Physical executor:** Sable receives an operator-authorized wheat-hauling assignment, physically delivers into an exclusive Create mill, and is attributed only when the direct Create processing callback is verified.
- **Pre-task source witness:** a different marked citizen personally observes the same physical source chest **before** the hauling job is assigned. This direct observation is an input to a special operator-assisted task-assignment gate, not post-hoc credit for being near a machine.

A second citizen's presence, secondhand report, updated/stale inventory memory, or matching timestamp is insufficient.

## Commands

```text
/sable haul-witnessed <source> <destination> <witness-entity-selector>
/sable mill-witness-probe <job-uuid>
```

The first command selects the nearest marked Sable executor, requires a *different* marked villager witness, and validates that the witness's `CitizenSourceKnowledge.directEvidence` contains a currently fresh, local, available-wheat `DIRECT_FORGE_OBSERVATION` for that exact source. The command is available only to permission-2 operators. If preflight fails, it creates **no hauling job or mill reservation**.

For a successful preflight, `SableHauling.assign` remains the authoritative physical assignment and writes a new job UUID and assignment tick. The witnessed-assignment bridge stores a versioned job-scoped record on the executor: world UUID, dimension, source, executor UUID, witness UUID, direct observation tick, source revision, wheat count, assignment tick and canonical witness evidence ID.

The second command independently joins that assignment link with the real Create process callback, an untainted current mill lease, the completed physical haul and the witness's original direct-memory revision. If any disagree—or the witness is unloaded—it denies without awarding credit.

## Scientific interpretation

The witness's direct observation was a **necessary gate for this explicit operator-assisted assignment**. This is a genuine observed dependency in the test action path, but it is **not** proof that the witness autonomously invented a recipe, that the executor independently chose the job, or that multiple learned agents formed a productive research collaboration.

No research/personal/colony points, durable credit delivery, recipe unlocks or gradient updates occur.

This does not add a second contributor to `OutcomeLedger`, and no imaginary weighted attribution is manufactured. A future policy must demonstrate an actual learned decision that consumes the witness report before multi-citizen causal reward can be granted.

## Acceptance

The Java 17 `DirectSourceWitnessContractTest` checks source/world/job identity, distinct citizens, timestamp ordering, a 40-tick pre-task observation window, report rejection, source revisions, physical process timing and replay mismatch.

The new `real-direct-witness-mill.yml` boots real Forge/Create. Its RCON fixture requires:

1. A second marked citizen without direct source evidence is **denied**, and no machine reservation is acquired.
2. The citizen performs a real `hearthbound citizen_observe` against an eight-wheat chest.
3. Only then does a witnessed haul get assigned to Sable.
4. The physical executor delivers one wheat and an actual Create `process()` callback produces flour.
5. The witness probe verifies the two roles and original pre-task link without awarding credit.
6. The witness subsequently observes the source's changed seven-wheat state, creating a new revision. The original two-role attribution is now denied, not retroactively rewritten.

The conventional unwitnessed experiment remains supported for the previously verified workflows. This is an additional operator-controlled research arm, not a change to general hauling or the agent action space.

## Unresolved research problem

The witness can be removed, unloaded or have their last direct memory overwritten. The currently captured link then cannot be independently revalidated, so the post-process probe fails closed. Future work should archive immutable witness revisions into the world-bound causal journal at assignment time, and then establish the behavioral counterfactual: **does the executor actually make a different decision when the independently delivered observation is withheld?** This will require a controlled scripted/MLP comparison and a shared source-selection policy, rather than simply assigning numeric witness credit.
