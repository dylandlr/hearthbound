# Citizen research attribution gate — v1

Minecraft runtime acceptance is established by [run 40159809558](https://github.com/dylandlr/hearthbound/actions/runs/40159809558): a real powered Create millstone consumed one wheat and produced flour, and the fixture's saved observation and durable credit survived restart. That run does **not** prove that any citizen performed the action. The Create hook explicitly recorded `researchCredit=false`.

`CitizenDiscoveryGate` is a standalone, pure-Java, fail-closed policy boundary for a later agent-controlled millstone. It requires an explicitly server-authorized assignment with an operation ID and beneficiary citizen, and a server-side observation matching that same operation, world, dimension, machine position, candidate/executed recipe, single input consumption and positive output delta. A missing assignment, recipe mismatch, or observation-only event cannot earn eligibility. Eligibility is **not** a credit transaction.

`CitizenDiscoveryGateTest` checks one valid case and rejection of null, unsigned/unowned, client-side, missing output, missing input, foreign operation, world, dimension, position and recipe mismatches. The standalone GitHub Java contract workflow now runs it.

## Remaining end-to-end integration
1. Create server-authored citizen work assignments with stable citizen IDs and operation IDs, persisted before milling begins. Never infer the citizen from proximity to a millstone.
2. Connect a completed Create mutation and the machine's durable intent to this assignment, using a stable operation ID across crashes/restarts.
3. Validate the real receipt against the assignment and pass it through `CitizenDiscoveryGate`.
4. Atomically persist the credit to the real citizen via `DurableCreditLedger` and expose discoverable knowledge in a colony agent state model; enforce idempotence, ownership and learning prerequisites.
5. Add a live Forge GameTest in which a citizen assignment causes the exact measured wheat operation and verify knowledge, teaching restrictions, and restart behavior.

This commit does **not** connect the real Forge hook to a citizen, award credit, or claim emergent discovery.
