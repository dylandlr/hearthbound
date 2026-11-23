# Bounded idle source discovery v0.12

## Problem and scope

The current #213 reliability cohort ran all five planned worlds; four passed
full acceptance.
In world 01, wheat remained at source x=4 while the board showed DONE=3,
ASSIGNED=0, and three physically completed history entries. This differs from
the earlier physical-delivery/accounting discrepancy. The source was within
the existing 16-block task/sensor range of idle citizens but outside their
small autonomous discovery scan. The [failed world remains archived](https://github.com/dylandlr/hearthbound/actions/runs/45133375442/artifacts/14798529666).

The previous revisions and cohorts retain their original results. #214's
test-only crash-verifier correction did not rerun or clear that colony trial.
This change is a new runtime intervention, based on #214 commit
`b25e33d1a9a8200e9862e6f88746c780d78eef82`.

## Runtime contract

Keep the existing immediate neighborhood scan and scripted queued-task ranking.
An enabled, idle citizen with no feasible queued candidate may spend one
additional discovery opportunity searching nearby positions. Active motors and
uncertain assigned/reserved/held jobs retain their existing handling.

The fallback uses the existing structured inventory sensor. It does not add a
visual or line-of-sight model. Its accepted observations remain limited to
already-loaded sources within the citizen's current 16-block spherical range.
The destination is the existing operator-registered colony destination.

Each fallback opportunity permits at most **75 candidate-position probes** and
**4 inventory-sensor calls**. Opportunities are separated by at least 20 game
ticks for a given citizen. Already-loaded and current-distance checks precede
block-entity lookup and inventory inspection. Skipped or unloaded positions do
not become EMPTY observations. Only a fresh AVAILABLE sensor result can propose
a task, and the normal dispatch path independently reinspects it before action.

These are incremental fallback limits. The existing immediate scan, queued
candidate checks, motor work, and other sensors have separate costs. Counting
sensor calls also does not impose a wall-clock CPU bound on arbitrary modded
inventory implementations. This change does not claim a measured server
performance improvement.

### Coverage and movement

A deterministic cursor enumerates a 33 by 3 by 33 anchored box, containing
3,267 candidate positions, with nearer horizontal offsets first. It excludes the citizen's **current** immediate
neighborhood from fallback inspection because that neighborhood is handled by
the original scan. Distance and vertical-neighborhood eligibility are checked
against the current citizen position on every opportunity.

Small movement preserves the cursor. Completing a sweep reanchors to the
current position. Displacement exceeding four blocks on either horizontal axis
or one block vertically resets the anchor; destination and scope changes also
reset the appropriate cursor. The anchor must not permanently
exclude its old immediate neighborhood: after movement, those positions may no
longer be covered by the citizen's current immediate scan.

For a stationary eligible citizen with loaded candidates, no resets, and a
nonbinding inventory limit, a sweep needs at most `ceil(3267 / 75) = 44`
opportunities. This is an algorithmic coverage bound, not a measured completion
time. Dense inventories can exhaust the four-inspection budget earlier, and a
moving citizen has no equivalent fixed coverage guarantee. No movement or
pathfinding behavior is added by the discovery scheduler.

## Evidence boundaries

The read-only discovery audit reports incremental counters, bounded recent
observations, and cursor state. At most 256 citizen cursors and 128 recent
observations are retained per dimension's session. Least recently advanced
citizen cursors and oldest observation records are evicted independently.
Counters describe the current retained cursor's lifetime, not an entire
session after eviction. The existing citizen tick schedule enforces the
20-tick opportunity cadence; the pure scheduler also rejects too-early calls
for retained citizens.

`hearthbound-colony discovery-audit` returns a compact session summary.
`hearthbound-colony discovery-audit <citizen UUID> [offset]` returns that
citizen's counters and at most two observations per page, with sequence IDs and
pagination metadata to avoid oversized RCON responses.
Each retained observation identifies its actual observer, world, episode,
position, source, tick, sensor result, and proposal outcome. Capacity and
eviction counters make incomplete retention explicit. Audit reads do not
resample inventory or manufacture knowledge.

Discovery diagnostics are session-scoped. Existing citizen memory can retain
direct observations, and persisted task/history records retain their existing
identity and restart rules. A cursor, remembered quantity, proposal, or audit
record cannot authorize physical completion or rewards.

## Validation requirements

1. Pure scheduler contracts cover coverage, per-opportunity budgets, inspection
   limit continuation, current-position checks, movement/scope reset, bounded
   retention, and nonmutating audit reads.
2. A separate live Forge fixture places real wheat outside the old immediate
   scan but within the existing sensor range. Its observation must record the
   citizen's actual position at inspection time, rather than rely only on the
   starting position. The fixture binds the observation and proposed task to
   a real decision, motor job, source depletion, destination increment, and
   persisted completion history.
3. A loaded source beyond sensor range remains untouched and unknown. An empty
   inventory must have an actual EMPTY observation and receive no task credit.
   Setup may prepare an arena; after dispatch is enabled, the fixture does not
   move citizens, enqueue tasks, refill inventories, or retry physical work.
4. Clean restart preserves physical inventories and authoritative completed
   task/history identities, with dispatch disabled. Session diagnostics are
   not interpreted as durable transaction receipts.
5. The existing independent-world workflow runs its unchanged five-seed cohort
   and retains all outcomes. Existing Create, hauling, communication, disabled-
   dispatch completion, restart, and crash checks remain relevant gates.

The four-citizen acceptance still requires four distinct completing citizens.
A citizen that already worked may discover and complete another source; that
can improve physical output while failing the distinct-worker gate. Multiple
jobs per citizen remain permitted. Neither a one-job restriction nor a relaxed
acceptance threshold is an acceptable way to make that gate pass.

Record the tested revision and protocol hash with every new cohort. Do not pool
this runtime intervention with the preceding #213 cohorts, or replace their
failures with successful reruns. Small fixed-seed pilots provide limited
frequency evidence even when every planned world passes.

## Research connections

The [research foundation](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md) names Project
Sid, MultiAgentBench/MARBLE, and the selected PA4 readings as primary guidance.
Project Sid's responsive module boundaries motivate keeping observation work
bounded alongside Minecraft execution. ReAct and the PA4 failure-analysis
readings motivate separate observation, decision, execution, and outcome
records. MultiAgentBench motivates keeping physical completion and worker
participation separate, including when an extra job changes their relationship.

These are engineering adaptations, not replications of the papers' results.
The new discovery budget and sensor behavior must be held equal across future
isolated-worker and communication-topology comparisons; otherwise extra direct
sensing could confound an apparent communication benefit. This scheduler is
scripted. It does not demonstrate learned exploration, causal communication
benefit, role specialization, or societal emergence.
