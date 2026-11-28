# C14-01: relevant sources and evidence boundaries

Reviewed: 27 November 2026 (user client date).

This is the source traceability record for [the scheduler contract](C14_EVENT_SCHEDULER_CONTRACT.md).
It records what was read, which design decisions it informs, and what still requires implementation
evidence. It does not assert that the proposed tests pass, that a native disruption adapter exists,
or that citizens demonstrate adaptation or specialization.

## Directly reviewed primary sources

### Pham: scheduling and delivery have different responsibilities

**H. H. Pham, “Software Agents for Internet-Based Systems and Their Design,” Chapter 5, Section 4**,
in Lakhmi C. Jain, Zhengxin Chen, and Nikhil Ichalkaranje (eds.), *Intelligent Agents and Their
Applications* (2002). Book DOI: [10.1007/978-3-7908-1786-7](https://doi.org/10.1007/978-3-7908-1786-7).

- **Reviewed location:** printed pp. 113–117; physical PDF pp. 131–135. Printed p. 114 / physical p. 132
  was also visually checked. Supplied project source: `0190-02 Springer Jain ag.pdf`,
  file ID `file_00000000808c81f689aaf9f21b9a2056`.
- **Finding:** the chapter separates communication language, send/receive procedures, scheduling,
  and delivery infrastructure. The infrastructure stores messages and retains communication links
  until recipient acceptance or delivery expiry.
- **Application:** keep a transition becoming due separate from its eventual settlement. The scheduler
  must preserve a pending delivery rather than treat advancement of a timeline cursor as completed work.
  This is a Hearthbound application of the lifecycle distinction; an experiment event is not itself
  an inter-agent message.
- **Validation motivated:** interruption after preparing an intent, restart with a pending intent,
  duplicate/conflicting receipts, and explicit missed delivery. The native adapter must separately
  reconcile physical effects.
- **Limit:** this source does not specify our journal, acknowledgement API, filesystem guarantees,
  or exactly-once world mutation. Those are engineering contracts requiring their own tests. Its
  historical implementation technologies are not Hearthbound dependencies.

### Chan et al.: identities and logs support inspectability

**Alan Chan et al., *Visibility into AI Agents***, FAccT 2024,
[DOI 10.1145/3630106.3658948](https://doi.org/10.1145/3630106.3658948),
[arXiv:2401.13138v6](https://arxiv.org/abs/2401.13138v6), 17 May 2024.

- **Reviewed location:** Section 3.1, physical p. 5; Sections 3.3–3.3.2, physical pp. 7–8.
  The configured [refs/m8-monitoring folder](https://drive.google.com/drive/folders/13Dc-SEH7DiCMQAoKgo-W_VceoQfUYtan)
  was inspected and the primary text of
  [chan2024-visibility-into-ai-agents.pdf](https://drive.google.com/file/d/1m7qqxJNFsoWmIaMXwzPhNBxum6HQjjUF/view)
  was read through Drive. The existing local primary PDF was used to verify page locations and v6;
  its SHA-256 is `5fa0de17952151268dc561b2100a0f9e3dd6392b7c92e5b56c1afeb1dc0416a9`.
  Byte identity between that local copy and Drive's readable-text response was not established.
- **Finding:** identifiers connect actions to particular agents; activity logs record inputs, outputs,
  and state changes. Persistent and combined logs can help investigate activity spanning lifetimes
  and multi-agent interactions. The paper also distinguishes logging detail and access scope.
- **Application:** bind scheduler evidence to world, run, immutable schedule, event, and transition
  identities. Keep attempted, failed, missed, unresolved, and settled states distinguishable. Diagnostic
  access to the experiment schedule must not implicitly become an actor observation.
- **Validation motivated:** reject foreign bindings, unknown transitions, conflicting receipts, and
  impossible histories; preserve pending evidence across restart. Actor information isolation requires
  a separate native integration test.
- **Limit:** visibility does not authenticate a physical outcome or establish causal benefit. The
  paper does not prescribe our record format, crash recovery, or receipt semantics. Its governance
  discussion is not an additional user-approval requirement for ordinary repository work.

### Project Sid: compare intended and observed outcomes

**Altera.AL, *Project Sid: Many-agent simulations toward AI civilization***,
[arXiv:2411.00114v1](https://arxiv.org/html/2411.00114v1), 31 October 2024.

- **Reviewed location:** Sections 2.3 and 3.2, plus Section 8.2 for the specialization measurement
  boundary; directly read from the versioned primary HTML.
- **Finding:** its action-awareness module compares expected action outcomes with observed outcomes.
  Its specialization method infers roles from generated social goals using GPT-4o, then examines action
  distributions by inferred role.
- **Application:** a native event adapter must distinguish the intended disruption, an accepted
  operation, and independently checked world effects. Keep job specialization as its own milestone
  with grounded behavioral evidence and a separate evaluation protocol.
- **Validation motivated:** an injection command or success receipt alone must not pass the physical
  disruption gate. Verify the actual world change; later measure occupation persistence and response
  to specialist loss using independently witnessed behavior.
- **Limit:** adopting this design principle does not reproduce Project Sid's result. It does not
  authorize LLM controllers, off-thread Minecraft world mutation, or interpreting role labels as
  verified emergence. The scheduler chooses neither occupations nor recovery behavior.

### MultiAgentBench: distinguish contribution from outcome

**Kunlun Zhu et al., *MultiAgentBench: Evaluating the Collaboration and Competition of LLM agents***,
[ACL 2025 publication](https://aclanthology.org/2025.acl-long.421/), pp. 8580–8622,
DOI `10.18653/v1/2025.acl-long.421`.

- **Reviewed location:** Sections 3.2–3.3, especially printed p. 8584 / physical PDF p. 5, directly read
  from the published-paper copy; publication metadata checked against ACL Anthology.
- **Finding:** the paper separately defines milestone contribution, a final task score, and
  coordination evaluation. Its benchmark scenarios also explicitly assign roles.
- **Application:** report scheduler correctness, successful physical injection, colony production,
  recovery, and occupational change separately. The experiment scheduler's own activity is not citizen
  participation, productive work, or successful adaptation.
- **Validation motivated:** keep distinct denominators for scheduled transitions, verified effects,
  completed colony tasks, and valid independent-world trials. Preserve failed and incomplete trials.
- **Limit:** authored benchmark roles are not evidence for Hearthbound's emergent job-specialization
  milestone. MARBLE is the accompanying implementation of the same research effort, not an independent
  replication. No new MARBLE revision was audited or executed for this scheduler change.

## Secondary reference: the supplied PA4 dossier

The user's `PA4_Reading_Reports (2).pdf`, file ID `file_00000000ddb081f68c9b38c1759ccf0c`, was read at
**P06, physical pp. 30–33**, and **P42, physical pp. 185–188**. These reports discuss observable
verification failures, causal ambiguity of failure labels, participation denominators, and the
distinction between coordination ratings and outcomes.

This is a secondary reading and analysis aid. It helps frame the primary-source checks above; reading
it does not constitute a new full review of every original paper it discusses. For disruption trials,
record injection failure, uncertain receipt, absent world effect, and failure to recover as separate
observations. These labels require evidence; they do not establish the underlying cause by themselves.

## Engineering decisions and remaining evidence

The journal hash chain, explicit acknowledgement/reconciliation API, bounds, canonical encodings,
writer exclusion, missed-tick policy, durable appends, and Java/Python parity are project engineering
decisions. The cited papers do not prove them correct. Their acceptance requires direct contract,
fault-injection, cross-language, and integration evidence as specified in the scheduler contract.

Likewise, the following are separate gates:

1. A scheduler delivers and records valid experimental intents.
2. A native adapter produces independently verified physical effects.
3. Citizens respond through their own available policy and observation interfaces.
4. Controlled independent-world evaluation supports any claim about recovery or learned adaptation.

Passing an earlier gate cannot substitute for a later one. Routine serialization and filesystem
mechanics do not need unrelated game-theory or LLM citations. Other `refs/` papers remain available for
the tickets where their mechanisms materially apply.
