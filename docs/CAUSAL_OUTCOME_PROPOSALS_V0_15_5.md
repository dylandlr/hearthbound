# Hearthbound v0.15.5 — causal reward proposal staging

This additive slice introduces `OutcomeLedger` (Java 17) as an **in-memory attribution proposal layer** for a candidate `VerifiedMillAttribution.Claim`. It deliberately does not enable any live research reward or training update.

It composes rather than replaces `DurableRewardLedger`, `AttributedMillInbox` and `ResearchJournalRuntime`: `OutcomeLedger` calculates deterministic credit proposals from job-bound decision records and a physical evidence identifier. The durable journal remains the journal of record **only after** independent world-identity, rollback and late-taint admission.

## Contract

- Immutable decision identity: world UUID, job identifier, citizen identifier, action and decision tick.
- Candidate claim: canonical `hearthbound:mill:v1:{world}:{dimension}:{job}` identity and valid process chronology.
- Contributors: previously registered decisions from the same world/job, timestamped no later than the observed process start; at least one matches the verified mill citizen. Personal and research weights may differ.
- Physical evidence: one evidence ID cannot be used for two outcomes. Replaying the identical outcome is idempotent; changing the attribution or budget is rejected.
- Domain isolation: personal/research budgets are divided independently with exact integer largest-remainder arithmetic; colony credit is granted once to the named colony account.
- `Award.toUncommittedCredit()` returns a **proposal**, never a server authorization. No live credit, recipe unlock or ML weight change occurs.

## Validation

Run `bash scripts/test-research-journals.sh` from the branch. `OutcomeLedgerTest` adds **34 local Java 17 contract checks** covering weighted attribution, deterministic replay, duplicate physical evidence, cross-world/job contributor denial, missing owner, future decisions, empty eligibility, domain splits and explicit durable-ledger test-mode delivery/recovery.

The test is a standalone contract test, not a Forge server or Create GameTest. Its only direct `DurableRewardLedger.credit` call is inside the test. In-game draining through `ResearchJournalRuntime.drainUnsafeForStandaloneTestsOnly()` remains forbidden.

## Integration prerequisites before live credit

1. Capture decision registrations from **trusted Minecraft executor receipts**, not invented decision strings.
2. Derive physical evidence IDs from authoritative untainted `MillProcessReceipts` rather than accepting a free-form caller string.
3. Revalidate Create physical state and taint at durable delivery, not merely when a proposal is built.
4. Reconcile NBT/SavedData, append-only inbox, world UUID, late taint and rollback across restart. Do not convert caller-supplied booleans to permission.
5. Run a real Forge/Create acceptance trial including multiple contributors, duplicate callbacks, taint/restart denial and explicit citizen teaching with a separate recipient evidence lineage.
6. Evaluate frozen scripted and neural baselines on held-out worlds before admitting any learned reward-driven policy.

## Explicit limitations

There is no autonomous discovery or successful recipe teaching in this milestone. No live Create callback submits to the proposal ledger, no online rewards are paid, and its decision/evidence maps are in-memory and do not themselves survive a server restart. The system currently distinguishes **recorded outcomes**, **credit proposals**, **durable credits** and **agent learning** as separate states.
