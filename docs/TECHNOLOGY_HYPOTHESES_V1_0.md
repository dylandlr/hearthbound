# Hearthbound v1.0 — Evidence-gated technology hypotheses

This increment introduces `TechnologyHypotheses`, a Java 17, LLM-free per-agent hypothesis state machine.

## Core research contract

Each proposed hypothesis names an agent, a proposed recipe, a hypothesized input item, a machine type and an expected output. Status begins as PROPOSED. A server-journaled `WorldEvidenceJournal.ProcessingEvidence` may confirm the hypothesis only if it is physically verified, references the same recipe and matches the proposed input, machine and output; otherwise an event for the correct recipe but incompatible observed input/machine/output marks the conjecture FALSIFIED. Unknown evidence and unrelated recipe evidence are rejected.

A confirmed hypothesis does **not** independently unlock recipes, grant rewards, or bypass `OutcomeLedger` or `CitizenTechnologyKnowledge`. Existing reward/knowledge writes must still be routed through the verified physical experiment coordinator.

## Scope of this commit

- Unit tests for proposed->confirmed, proposed->falsified, unknown/unrelated evidence rejection, conflicting proposals and exact evidence replay.
- Pure Java hypothesis state machine, decoupled from Minecraft internals for simulator training.
- Deliberately no mutation of physical inventory or recipe registry.

## Limitations and next integration

The journal contract currently accepts `physicallyVerified` records but the new hypothesis ledger does not itself authenticate the Create callback. Use only the existing trusted Create event adapter and receipt flow at runtime. The hypotheses currently live in memory and are not yet bound to villager NBT or `SavedData`.

Next: connect the runtime's trusted Create receipt to the hypothesis state machine, persist hypothesis ownership, add exploration actions conditioned on partial observation, and run Minecraft smoke tests with deliberate false hypotheses. Do not describe this module alone as proof of emergent scientific discovery.

## Acceptance criteria

A scripted baseline and an MLP-based decision policy must receive the same partially observable technology investigation state. Compare validated discovery latency, resources consumed, incorrect conjectures, and quality of physical evidence across held-out seeds. Never reward a hypothesis merely for being declared.
