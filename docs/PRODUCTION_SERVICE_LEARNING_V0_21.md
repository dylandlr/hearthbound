# Production services and private learning, v0.21

This change extends the opt-in need-service runtime from wheat transport to a complete Create production service. The intended unit of work is **satisfy a locally observed flour shortage**. A citizen remains responsible through wheat transport, processing, output custody, and delivery. A physical input transfer is an intermediate event.

## Research and supplied course material used

Reviewed 24 November 2026. These sources inform the implementation; their published results are not Hearthbound results. The general research mapping remains in [the foundation document](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md).

| Supplied or primary source | Specific design consequence in this change |
| --- | --- |
| [CSCE 631 `refs glossary.txt`](https://drive.google.com/file/d/1s3vouEnSdk11b5D2PTgknc95FU_Ppm4C/view), modules 3, 4, and 6 | Select bounded, sustained service actions from a citizen's information. Save the actual decision context before executing; learn from the realized duration and outcome. Public site geometry does not reveal private stock or another citizen's memory. This is a contextual value learner, with no claim of a regret guarantee or solved extensive-form game. |
| [Sandholm, *Abstraction for Solving Large Incomplete-Information Games* (2015), supplied `refs/m6-abstraction`](https://drive.google.com/file/d/1XZ0nmTWYx7hTxHx59fMyKw60UaqdEggQ/view), sections on information/action abstraction and abstraction pathology | The service vocabulary is an explicit action abstraction. Retain physical execution and outcome witnesses outside that abstraction. More detailed actions or a finer representation do not automatically establish better policies, equilibrium, or transfer guarantees. |
| [Cemri et al., *Why Do Multi-Agent LLM Systems Fail?*, supplied `refs/m7-multiagent`](https://drive.google.com/file/d/1ZqnYhCQ0eAXYy2ScVFGW8HQP0Zit8EH-/view), arXiv:2503.13657v3, taxonomy and task-verification discussion | Distinguish premature completion, missing verification, repeated work, expired information, and conflicting ownership. A wheat insertion, a Create callback, a collected item, a delivered output, and a final learner update have different records. MAST is applied as an engineering diagnostic; this non-LLM runtime is not a reproduction of its evaluated systems. |
| Supplied *PA4 Reading Reports*, P42, physical pp. 185–188 | Report physical completion, contribution distribution, and coordination costs separately. Packet-to-recipient-production provenance is an association, not an estimate of causal communication benefit. A single live acceptance is not a policy comparison. |
| Supplied *PA4 Reading Reports*, P28 and P37, critical assessments and course connections, physical pp. 124–125 and 166–167 | Keep feedback quality and action–observation provenance explicit. Persisting a memory, changing model parameters, and improving task performance are separate claims. A peer report can justify a decision but cannot serve as independent proof that its requested work finished. |
| Supplied *PA4 Reading Reports*, P32 and P33, assessment and PA4 implications, physical pp. 142–143 and 148–149 | Freeze complete policies and protocols before a comparison; preserve world-level outcomes and matched conditions. Future occupation or coordination studies need off-diagonal policy profiles and checked deviations before strategic-stability claims. More samples do not repair a missing strategy or an invalid symmetry assumption. |
| H. H. Pham, “Software Agents for Internet-Based Systems and Their Design,” supplied *Intelligent Agents and Their Applications*, physical pp. 131–135 (printed pp. 113–117) | Preserve the separation between message representation, send/receive transport, scheduling, and resource limits. A delivery acknowledgement cannot be treated as task completion. Retain expiry and unresolved states. |
| [Project Sid, arXiv:2411.00114v1](https://arxiv.org/html/2411.00114v1), §§2.1–2.3 and 3.2 | One action owner coordinates persistent options while lightweight world execution remains responsive. Compare expected actions with observed changes. All Minecraft mutations remain on the server thread; PIANO's concurrency does not justify competing motors or off-thread world access. |
| [MultiAgentBench, ACL 2025](https://aclanthology.org/2025.acl-long.421/), task and milestone evaluation; [MARBLE implementation](https://github.com/ulab-uiuc/MARBLE/tree/eae9f15e5b9f1e808f8ff61800b129d5538c1b47) | Pin the implementation and preserve the complete event chain, independent inventories, all failed runs, and exact scenarios. Completion is separate from participation. No topology superiority is assumed. |

The consulted MARBLE revision is `eae9f15e5b9f1e808f8ff61800b129d5538c1b47`, committed 16 November 2026, tree `57e40328c22b0b3cde33afa2d0a7509e8e9c5f40`. Its maintained code and the published ACL article are separate versioned sources from the same research effort. No MARBLE code, LLM dependency, API credential, or paid inference path is introduced.

## Physical service contract

The operator may register source, mill, and destination geometry and a stock target. This configuration describes available infrastructure. Citizens still need a direct local observation or an actually delivered private request before selecting work.

1. A citizen locally observes the configured destination's flour stock and forms a timestamped shortage request.
2. An eligible citizen chooses a service using its own request book, fresh source observations, and private learner. The executor arbitrates the resulting claim against current capacity and machine ownership.
3. The existing native wheat motor transports one wheat to the reserved Create millstone. Its receipt proves input transfer only.
4. The same commitment remains occupied during processing. The citizen's original native job and mill trace remain bound; another assignment cannot overwrite them.
5. A real Create callback, independently observed processing start, matching reservation, untainted provenance, and actual output inventory authorize nearby collection. The actual flour delta determines quantity; a presumed recipe yield does not.
6. The citizen carries the actual output to the destination. Before/after inventory checks establish insertion. All material is preserved, including surplus and any supported byproducts.
7. Final revalidation, safe reservation release, demand settlement, and private learning complete the service. The completed mill trace is retired so it cannot falsely compete with another citizen's later job at the same machine.

A batch reserves at least one outstanding demand unit; its final actual flour quantity settles demand. This can produce surplus from a variable-yield batch. The implementation preserves and reports that surplus rather than deleting it or miscounting wheat as flour. Exact-output reservation would require a separately justified yield model.

## What learns

Each citizen owns a separate online value model. It retains the selected candidate's features, decision time, and identity before world execution. Settled outcomes update estimated service duration, measured personal cost, and completion. Verified final production updates the supply option's output estimate. Positive supply output cannot leak through shared regression features into fabricated output estimates for waiting, observing, or carrying a request.

The baseline algorithm is recursive least squares over bounded features. It is neither deep reinforcement learning nor a reproduction of Project Sid's LLM controller. The service/observation/settlement boundary is intended to support a later trained MLP or recurrent controller without changing which physical facts count as outcomes. Existing frozen v0.17–v0.19 experiments remain unchanged.

Input transfer alone cannot train the production head. An unresolved or unobserved production outcome stays unknown. Decision-time context is not reconstructed later from changed world state. Foreign citizen outcomes, duplicate jobs, duplicate physical evidence, and mismatched replay are rejected.

The supplier can learn from its own complete productive service. A request sender is not secretly updated from the recipient's remote outcome. The event log retains the exact packet → recipient decision → job → delivered production chain for analysis. Courier contribution learning will require an explicit feedback channel and its own attribution contract.

## Termination and persistence

After the stock target is satisfied, fresh local observations close demand. Existing private reports can remain stale until a citizen observes closure or their original evidence expires. Safety arbitration prevents new physical claims against exhausted capacity. Expiry, capacity gates, and authored monitoring behavior must not be presented as learned occupational withdrawal.

Stopping before pickup can cancel a proven empty native job. Stopping during processing or output custody retains the commitment, reservation, and any cargo in a held state. Restart never silently resumes ambiguous inventory mutations, frees unresolved material, or awards production again. Completed private learner history is replayed with the same owner and world scope.

Minecraft entity NBT, block inventories, and SavedData are not a single transactional database. Mutation intents and held restart states provide fail-closed handling; this change does not claim arbitrary power-loss atomicity across chunk saves. Clean completed restart and unresolved processing restart are separate acceptance cases.

SavedData schema 2 stores the kernel, event history, and private learner JSON
as UTF-8 byte arrays. Growing histories can exceed NBT's modified-UTF string
limit; schema-1 string saves remain readable. Invalid encodings or unexpected
payload types fail closed. The real-NBT `servicePersistenceContracts` gate
round-trips large histories and Unicode without truncating retained evidence.

## Acceptance and claim boundaries

The dedicated live scenario uses two equally capable citizens, one public wheat source, a powered real Create millstone, and a separate flour destination. After start, the fixture issues no movement, handoff, pickup, processing, output-collection, or completion commands. It requires multiple batches through the same mill, independent native inventory witnesses, a received-request-to-production chain, actual private learner updates, subsequent scored decisions, and a natural target-closure window. It also checks completed save/restart and a separate held-processing save/restart with an unpowered mill.

The scenario is an engineering acceptance under a fixed fixture. It cannot establish improved sample efficiency, causal communication benefit, generalization, a learned courier occupation, or emergent society. Those claims require frozen policies, independent worlds, matched controls, and cost accounting. The broader four-citizen reliability gate remains a separate requirement; a green production fixture cannot erase its failures.

See the accompanying playtest and recorded CI evidence for the observed results and exact revision.
