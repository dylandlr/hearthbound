# Colony delivery reconciliation v0.10

## Problem demonstrated by the preceding live cohort

The [PR #212 five-world cohort](https://github.com/dylandlr/hearthbound/actions/runs/45125525273)
tested commit `5efe9d9f71cfe7c7c3053d77b5625863fd98a878` with protocol
`3f71b2e1ac5389408f1af7b62cb99346a50614831d01c0219ad281e5f003ee5e`.
All five planned worlds ran, and every failure remains in the
[archived summary](https://github.com/dylandlr/hearthbound/actions/runs/45125525273/artifacts/14795623104).

| World / seed | Physical result | Task board and history | Failure |
| --- | --- | --- | --- |
| 01 / 43101 | Four deliveries, zero claims | DONE=2, ASSIGNED=2; history complete=2/4 | Physical/accounting disagreement |
| 02 / 43102 | Three deliveries; source x=4 retains wheat | DONE=3, ASSIGNED=0; history complete=3/3 | Missed source |
| 03 / 43103 | Three deliveries; source x=12 retains wheat | DONE=3, ASSIGNED=0; history complete=3/3 | Missed source |
| 04 / 43104 | Four deliveries, zero claims | DONE=2, ASSIGNED=2; history complete=2/4 | Physical/accounting disagreement |
| 05 / 43105 | Three deliveries; source x=4 retains wheat | DONE=3, ASSIGNED=0; history complete=3/3 | Missed source |

For worlds 01 and 04, independent inventory reads found all four source chests
empty and the destination holding four wheat. The reconciliation audit
identified two loaded citizens with completed physical jobs still recorded as
ASSIGNED. The discrepancy persisted from the first progress audit to the end
of the full 150-second observation window.

All four stale owners were at block z=-1; the fixture force-loads only the
rectangle from (0,0) to (31,4). Their peers whose board jobs were DONE remained
at z>=0. Before this change, `SableController` returned after the motor tick,
and the board/history could only reconcile on the owner's next eligible
living tick while dispatch was enabled. A citizen leaving the ticking area
therefore supplies a plausible mechanism. The old artifacts did not record
the chunk's entity-ticking status, so the positional explanation remains an
inference. The deferred-completion dependency is directly visible in code.

## Implementation boundary

A successful physical insertion already removes carried cargo, records the
delivery tick, marks the motor complete, and releases its source claim. The
colony adapter now validates that completed motor receipt immediately and
updates the matching existing task and decision history on the same server
thread. It does not depend on another dispatch tick.

New assignments bind the motor receipt to the authoritative world UUID.
Receipts must also match dimension, citizen, job, source, destination,
assignment tick, and valid delivery chronology. Matching an item count or an
agent's claim cannot authorize completion. Unknown jobs, foreign receipts,
mismatched assignments, and uncertain HELD/reserved states cannot acquire
completion credit. Legacy saved jobs without the new world field retain their
existing eligibility through the current world's board and exact assignment
binding; they do not gain independent world provenance retrospectively.

Revisiting a DONE assignment cannot add or change a task. The task board does
not retain a delivery timestamp; the separate decision history does and
rejects conflicting timestamp replays. This distinction prevents describing
task-state idempotence as full receipt-history validation. The existing
idle-tick reconciliation remains a fallback for a valid completed assignment.

Disabling dispatch prevents new work. It does not prevent bookkeeping for
already assigned work that the existing hauling motor is allowed to finish.
The callback never repeats insertion, retries a job, changes an inventory,
authorizes a reward, or creates a task. Ordinary direct hauls do not become
colony work. Exceptions in completion bookkeeping are logged after the motor
has finished; they cannot send the motor back through a physical operation.

SavedData retains its existing persistence semantics. This is not a new
crash-atomic transaction spanning entity state, inventories, and task history.
The existing pickup/delivery journal and recovery gates retain authority.
After a restart, a valid old assignment can reconcile on the board while its
previous-session research entry remains incomplete under the existing
episode fence. No new-session research credit is fabricated to fill that gap.

## Regression that exercises the lost-follow-up dependency

`scripts/rcon_colony_completion_boundary.py` runs a separate controlled Forge
fixture, leaving the existing four-citizen fixture unchanged:

1. One real citizen receives an autonomous colony haul. Dispatch is disabled
   while the job is assigned and before the item reaches the destination.
2. The existing physical motor finishes. Source, destination, claim, task,
   and history witnesses must agree while dispatch is still disabled.
3. The same citizen completes a second distinct job under the same condition.
   Multiple jobs and future specialization remain possible.
4. A separate direct haul moves a third item without adding colony task or
   decision-history credit.
5. A clean restart preserves the completed board/history and leaves dispatch
   disabled. Read-only inspection cannot create duplicate completion records.

The original implementation cannot satisfy the disabled-dispatch completion
check: its only accounting path returns before reconciliation when disabled.
This isolates the missing follow-up dependency without needing a stochastic
chunk crossing or changing the original pilot's forced area or timeout.
Fixture setup between rounds is explicit and is not counted as agent work.

Pure Java contracts additionally reject invalid receipt identities,
chronology, endpoints, uncertain states, and conflicting assignment replays.
Actual Forge
compilation and the live regression are separate gates. Their source of
truth is the new draft PR's exact tested head and attached workflow artifacts.

## Keep the historical event and its broader variant separate

The frozen `three_of_four_accounting_event` still means physical four,
DONE=3, ASSIGNED=1 in both terminal reads. It was 0/5 in the preceding cohort;
its approximate 95% Wilson interval was 0–43.45%. That does not imply absence
of accounting failures: two worlds instead had DONE=2, ASSIGNED=2.

The additional `physical_delivery_accounting_event` prospectively measures
four verified deliveries and zero claims, with stable, plausible terminal
task counts, DONE<4 and ASSIGNED>0 after the full observation window. It has
its own observed/assessable/unknown counts, descriptive Wilson interval, and
planned-cohort missingness bounds. A changing snapshot or impossible fixture
counts are unknown for this added metric. The original event, classifications,
acceptance gate, and archived reports are unchanged.

Applied descriptively to the preceding records, the broader signature is
2/5 (40%; approximate Wilson interval 11.76–76.93%). That is a reanalysis of
the existing cohort, not five additional trials or a predeclared original
endpoint. The next cohort pins the expanded evaluator in its protocol hash.
Do not pool different revisions or protocols into a claimed treatment effect.

## Remaining work and research connection

The three missed-source failures have no pending assignment to reconcile.
Citizens near the destination can be within the 16-block task-menu sensor
range but outside the small autonomous source-discovery scan. A separate
observation/discovery improvement needs its own evidence and evaluation.
Unequal worker participation, seen in the earlier #211 pilot, is also distinct
from physical delivery and accounting. No one-job-per-citizen cap or weaker
four-citizen acceptance criterion is introduced here.

[Project Sid](https://arxiv.org/html/2411.00114v1), especially its module
coordination and action-awareness discussion, motivates keeping physical
execution and recorded outcomes coherent across different decision cadences.
[MultiAgentBench/MARBLE](https://aclanthology.org/2025.acl-long.421/) motivates
separating completion from participation. The PA4 MAST and ReAct readings
support explicit failure labels and observation/action/outcome traces; the
EGTA readings support reporting experimental coverage and uncertainty. These
are design connections, not replications or proof of improved learned
coordination. Exact sources and transfer limits remain in
[the research foundation](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md).

The next communication-network comparison still requires matched isolated,
exposed, and control conditions over independent worlds. Existing sender,
recipient, decision-use, and physical-outcome records establish provenance;
they do not by themselves establish a causal benefit from communication.
