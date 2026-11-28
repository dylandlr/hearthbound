# C14-01 seeded scenario acceptance record

Parent: [C14-01 / #233](https://github.com/dylandlr/hearthbound/issues/233).
Development baseline: `7cf3730e64433849c56952f88780284f8f98b2a0`, the verified delivery-core head
of draft [PR #234](https://github.com/dylandlr/hearthbound/pull/234).

**Ticket remains open.** This addition implements deterministic seeded block-target planning and
an enforced manifest/journal binding. It does not apply a Minecraft disruption or prove that a
native sham preserves state. It changes neither citizen policy nor the existing v2 journal protocol.

## Requirements recovered and mapped

The original backlog requires exogenous events with start, duration, severity, scope, deterministic
seed reproduction, and sham controls. An explicit event list was insufficient to satisfy generation;
an empty schedule was insufficient to demonstrate a native sham. This layer addresses those gaps in
planning while retaining their native acceptance conditions.

| Requirement | Implemented evidence | Remaining gate |
| --- | --- | --- |
| Same frozen config and seed reproduce choices | Specified SHA counter/rejection algorithm; fixed seed 0, 7 and Long.MAX_VALUE oracles; reordering invariance | Native world execution can still differ and must be measured |
| Validated onset, duration and severity | Signed-long bounds and worst-case end check; integer ppm severity; full-width tests | Adapter must respect current tick and define severity's physical meaning |
| Immutable scope and target configuration | Explicit dimension, permitted box and target positions; canonical scope/config/target hashes; target containment checks | Minecraft dimension, height, border, loaded-state and block-state validation |
| Configuration bound into experiment identity | Full manifest regeneration; config-bound event IDs; journal wrapper derives run identity from manifest and original trial | Native adapter must use the correct wrapper and scope descriptor |
| Empty controls retain identity binding | Changed seed, mode, scope or trial cannot reopen the same no-event journal despite an identical empty schedule hash | Native matched-world controls and trial provenance |
| Explicit sham planning | Same latent choices as treatment; zero effective severity, explicit sham mode and separate identity | Independently witness physical state preservation; zero severity is not proof |
| No-event planning | Latent choices retained; no event emitted | Distinct from sham activity and not a substitute for it |
| Durable lifecycle remains intact | Wrapper reopen preserves pending recovery holds and rejects blind ACK after restart; existing delivery regression suite retained | World/save/journal reconciliation still requires native evidence |
| Java/Python equivalence | Byte-identical manifests, fixed hashes and bidirectional journal reopening; independent change review completed | Strict Java 17 exact-head CI |

The first scope version supports `crop_failure`, `mill_failure`, and `resource_depletion` only.
Entity and channel event scopes need separate typed contracts; unsupported kinds fail rather than
receiving guessed block semantics. This does not remove those features from the backlog.

## Design and review artifacts

- [Versioned scenario contract](C14_SEEDED_SCENARIO_CONTRACT.md): input bounds, byte grammar,
  domain-separated hashes, unbiased draws, paired modes, run binding, and limitations.
- [Fixed independent fixtures](../tests/fixtures/event_scenarios/README.md): nine manifests and
  separate latent-choice oracles; tests do not regenerate expected outputs.
- [Existing source traceability](C14_EVENT_SCHEDULER_REFERENCES.md): relevant prior reference review,
  engineering applicability, and limits. No new paper result or source-reading claim is introduced.

## Phase status and execution evidence

| Phase | Status |
| --- | --- |
| Requirements and design | Original seeded/scope/sham requirements mapped; scenario-v1 and unchanged delivery-v2 boundary specified |
| Test design | Fixed oracles, forced rejection, wide numeric ranges, malformed/config drift, input-order and deep-immutability checks, paired modes, and wrapper restart cases implemented |
| Implementation | Isolated Python and pure Java source; no native registration or actor-facing API |
| Review | Independent implementation, contract, fixture and workflow review completed; publication and exact-head CI remain separate gates |
| Local functional QA | Consolidated development execution passed: 20 existing delivery Java groups, 11 new scenario Java groups, and 58 Python/cross-language tests (41 existing plus 17 new) on the available Java 21 runtime |
| Java 17 CI | Runner remains strict `--release 17`; no new workflow was launched during implementation |
| AI validation | No model, observation, reward or role change; not applicable to this generator-only addition |
| Native validation | Physical disruption, scoped execution, sham preservation and future-event isolation not executed |
| Integration and acceptance | Open; no merge or ticket closure implied |

Local Java 21 functional execution cannot establish Java 17 target compatibility. The available slim
runtime lacks release-17 symbols. The retained runner must record that compile failure when used in
this environment; it must not silently remove `--release 17`. CI supplies a complete JDK 17.

The local consolidated run compiled the experiment sources through Java 21's compiler module,
ran both Java test mains with assertions enabled, and ran Python unittest discovery for
`test_event_scheduler*.py` with that development classpath. All four development stages exited
zero; source and fixture hashes were unchanged during execution. This was an uncommitted working
tree on the stated baseline, not a new exact-head CI result. The 58 Python tests completed in
11.942 seconds; this duration is execution evidence, not a performance claim.

A separate invocation of the unmodified strict-release option stopped at `compile_java17` with
exit code 2 and `error: release version 17 not supported`. Its manifest reports overall failure,
all three subsequent test stages as `not_run`, `compile_release: 17`, and both native scope/sham
flags as false. No successful Java 17 validation is inferred from the development run.

The runner manifest now uses schema version 2 to include the additional Java scenario stage, all
scenario source/config/fixture hashes, and explicit false flags for native scope enforcement and
native sham state preservation. This runner-manifest version is separate from the unchanged v2
journal protocol and scenario-v1 content version.

Independent review on 27 November 2026 (America/Chicago) recalculated all nine latent-choice rows
directly from the specification and explicit fixture values, without importing either production
implementation. Every row matched the fixed oracle. A separate wrapper probe rejected seven
changed empty-schedule contexts (seed, mode, trial, scope removal, dimension and permitted box),
rejected a foreign world, reopened the original identity at cursor 5, and verified that rejected
opens did not change journal bytes. All inputs hashed by the consolidated functional run still
matched. This is review evidence, separate from the reported unit-test totals and native validation.

## Next native work

For the crop adapter, bind its physical operation contract and expected world preconditions, check
the selected dimension/region/targets on the server thread, and record independent before/after
world witnesses. Verify treatment loss and unchanged sham/no-event controls with complete failure
denominators. Respect v2 missed-tick and uncertain-restart behavior; never automatically repeat a
possibly applied mutation or restore crop inventories at an end transition.

The generated plan stays experiment-private. Actual integration must prove no future event, seed,
scope selection or planned severity leaks into actor observations, messages, rewards or learner state.
Only subsequent independent-world experiments can support claims about adaptation, learned recovery,
occupation persistence, or job specialization.
