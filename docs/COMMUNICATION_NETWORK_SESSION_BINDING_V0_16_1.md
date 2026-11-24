# Network observation session and episode binding correction

## Observed defect and retained source

The first PR #219 source, `c1184bdf2b59c720e4f66d42440fe63e23130a4d`,
passed actual Java 17 contracts and ordinary/forced cold Forge compilation.
Its new network qualification nevertheless entered a runtime error at the
first eligible send. The first retained NO_MESSAGES and DIRECT worlds report
`Outgoing payload does not match the sender's native direct evidence`.
The failure occurred before a complete 600-tick observation window; it is an
invalid runtime observation, not a measured zero-output world.

The new sender guard compared two different identities. `SourceReportSession`
stamps native observations with the random server-lifetime session UUID. Its
decision episode is a separate UUID derived from the world, server session,
and dimension. The raw session must not equal that derived episode. A similar
assumption in the new native-inbox validator would also have rejected genuine
delivered reports after the runtime guard was repaired.

All six original qualification slots remain attached to their original source
and workflow run [45324299503](https://github.com/dylandlr/hearthbound/actions/runs/45324299503).
The first cohort is not rerun, replaced, rescored with corrected code, or pooled
with the correction's later cohort. The original five-world reliability
cohort, legacy pilot, and controlled diagnostic remain separate as well.

## Correct identity contract

The correction keeps the existing native report fence and source observations
intact. The new network sender still requires the exact owned source,
observation tick, state, quantity, positive revision, and world identity. It
also requires the existing current-session fence to accept the observation.
It never restamps a peer report or changes native transport authority.

Each actual SEND now preserves two explicitly named fields:

| Field | Meaning |
| --- | --- |
| `observation_session` | The unchanged native server-lifetime observation session UUID |
| `observation_episode` | The decision episode derived from the observation's world, raw session, and dimension |

The derivation is exactly Java `UUID.nameUUIDFromBytes` over the UTF-8 bytes of
`worldUUID + "|" + sessionUUID + "|" + dimension`. It uses MD5 with UUID version
3 and standard variant bits. Python's namespace-taking `uuid.uuid3` function
is not interchangeable with that operation.

The independent validator recomputes this episode and requires it to equal
the world-scoped runtime episode. It binds each native inbox entry's raw
session through its exact SEND/native-attempt/message chain. The native
session cannot be substituted by a message's derived episode. Missing,
extra, altered, wrong-world, wrong-dimension, and wrong-session evidence must
fail validation. No-payload opportunities retain explicit null identity
fields and do not become send attempts.

Because the closed SEND payload changes, the new runtime schema and response
prefix advance to `hearthbound.communication-network-trial.v2` and
`COMMUNICATION_NETWORK_TRIAL_V2`. The legacy two-condition runtime retains its
v1 schema, commands, policy, transport, and scoring behavior.

## Validation and next first-outcome cohort

Targeted contracts must cover genuinely distinct session and episode UUIDs,
the exact derivation, valid native delivery and inbox replay, and rejected
identity tampering. Actual Forge compilation and a new six-slot first-outcome
qualification remain required; unit checks alone cannot establish the live
integration.

The correction's engineering cohort retains exactly the same predeclared six
conditions, world seed 56101, policy seed 66104, seat permutation `[2,0,3,1]`,
600-tick horizon, 30 rounds, budgets, graph permissions, coverage requirements,
and maximum concurrency of two. Every slot receives a new JVM/world/session
and one first attempt. A source correction changes the source/protocol
identity; it does not authorize replacement observations within the old cohort.

The frozen 144-world study, seeds 55101–55124, design, generator, and analysis
rules are unchanged. Its execution guard and runtime seed exclusion remain
closed. No expanded-study world is launched by this correction.

The original accounting discrepancy and active-haul failure remain unresolved.
In the `c1184bdf` reliability cohort, all five original physical/accounting
windows passed, while one later diagnostic capture was incomplete after a
completed citizen died and became unavailable. That missing observation is
retained as unknown. It does not become an empty-cargo assertion or erase the
original frozen score. No repair, altered footprint, or rescore is introduced.

Project Sid, MultiAgentBench/MARBLE, and the selected PA4 readings remain the
[research foundation](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md). This correction
addresses evidence identity and runtime reliability. It does not establish
communication benefit, learned collaboration, LLM control, equilibrium, or
societal emergence. Actual source-specific outcomes belong in the draft PR
and retained evidence archives.
