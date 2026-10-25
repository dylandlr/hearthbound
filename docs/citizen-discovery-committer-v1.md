# Citizen Discovery Committer v1

The first real Minecraft milling and restart evidence remains [run 40159809558](https://github.com/dylandlr/hearthbound/actions/runs/40159809558). Citizen attribution is still not hooked to Forge.

`CitizenDiscoveryCommitter` performs two sequential operations: (1) reject an observation not matching a server-authorized `CitizenDiscoveryGate.Assignment`; (2) persist a one-unit research credit in the existing append-only `DurableCreditLedger` keyed by operation UUID and citizen UUID. Replays with the same receipt return `newlyCredited=false`. Conflicts fail; storage errors must propagate. Balance is recovered from disk, not an in-memory counter.

`CitizenDiscoveryCommitterTest` checks the first write, duplicate replay, new-instance restart, conflicting receipt rejection, and rejected-output evidence not changing credit. CI executes the tests in its standalone research job.

## Explicit limitations
- The Forge server does **not** yet persist or supply an actual citizen assignment. The operation UUID and receipt must come from a verified, durable Create operation; never construct them from an untrusted client packet.
- The committer validates the provided assignment/observation contract, **not** independently the receipt string's contents. A future adapter must bind a canonical receipt to actual saved operation proofs before invoking it.
- The ledger records research credit units, not known-recipe sets, skill levels, AI decision trajectories, or teaching events. Do not call credit alone a learned technology.
- The current runtime Create callback still explicitly reports `researchCredit=false`.

## Next live acceptance gate
Persist server-owned citizen assignment before milling; attach its stable operation UUID to the machine's durable intent; verify observed Create process against the receipt and assignment; write credit; restart and verify the named citizen owns exactly one persisted research event. Only then expose recipe knowledge to the agent observation space.

## Runtime attribution fixture extension
The Forge GameTest now feeds the *real* observed milling record and a prepared durable operation intent through CitizenDiscoveryCommitter with a fixed fixture citizen UUID. It verifies exactly-once credit and re-checks after a separate dedicated-server restart. The fixture directory `hearthbound-fixture-citizen-credits` is separate from production citizen data. These tests establish transactional integration, not an autonomous actor, policy decision, or learned recipe knowledge.

## CI follow-up
The first citizen-credit acceptance request failed in the evidence-packager unit test before Minecraft could run (Forge compilation passed). The fix updates the required GameTest/restart marker partitions and their self-test fixture. The subsequent acceptance request is an explicit EULA-authorized rerun; its outcome requires checking the linked CI job and archived logs.

## Push-run observability
GitHub PR checks and push checks for the same SHA are distinct. The PR workflow is expected to skip Minecraft acceptance. An independent, early `experiment-launch-index` job on explicitly tagged *pushes* writes the push run ID to issue #77 before build/test jobs can fail. Follow that run ID to inspect the actual acceptance job; absence of a launch entry is a trigger or permissions problem, not a Minecraft pass.
