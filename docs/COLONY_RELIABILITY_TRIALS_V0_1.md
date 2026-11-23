# Independent-world colony reliability pilot

## Question and unchanged acceptance boundary

An earlier live four-citizen run delivered four wheat items but retained three
completed tasks and one assigned task. A later passing run does not establish
that this intermittent accounting failure has been fixed. This pilot repeats
the existing `rcon_civilization_four_citizens.py` acceptance fixture without
changing its dispatch, physical delivery, source-claim, history, trace, or
timeout requirements.

The experimental unit is a **new Minecraft world in a new server process**.
Four citizens inside the same colony are not four reliability replicates.
This fixture exercises autonomous scripted local-source task selection. It
does not estimate a communication-network effect, learned collaboration, or
societal emergence.

## Predeclared pilot

`.github/workflows/real-colony-reliability.yml` launches five matrix jobs with
`fail-fast: false`:

| Trial | Numeric Minecraft seed | Fresh level name |
| --- | ---: | --- |
| world-01 | 43101 | colony-reliability-world-01 |
| world-02 | 43102 | colony-reliability-world-02 |
| world-03 | 43103 | colony-reliability-world-03 |
| world-04 | 43104 | colony-reliability-world-04 |
| world-05 | 43105 | colony-reliability-world-05 |

Each job checks out the PR head SHA explicitly. It compiles Forge, creates
`server.properties` exclusively, refuses an existing world directory, boots
one server, runs the original fixture once, collects read-only terminal
diagnostics, saves, and stops. No world is deleted, no failed trial is retried,
and no outstanding task is repaired. The summary depends on the complete
matrix and runs even when a matrix job fails.

The seeds are fixed in advance for reproducibility. Minecraft world and entity
UUIDs and server scheduling can still vary between runs. This is a small,
controlled fixture cohort, not a random sample of ordinary player colonies or
proof that every source of stochasticity has been independently seeded.

## Provenance and retained evidence

Each trial artifact contains:

- Tested source commit and a protocol hash over the fixture, RCON helper,
  runner, summarizer, and workflow.
- The actual configured seed and level name.
- The generated seed read from saved `level.dat` and the world UUID read from
  Hearthbound's saved world identity, with retained copies and hashes of both
  small metadata files. The summarizer rechecks these and the log hashes.
- Complete server and RCON logs, their hashes, fixture errors, and terminal
  source/destination/claim/task/history diagnostics.
- An explicit indication of whether the original fixture passed or reached
  its complete observation deadline.

The legacy fixture's receipt contains a constant `fixture_seed` and
`fixture_world`. Those fields continue to describe the fixture template.
**They are not used as the new world's seed or identity.** The new trial
record's saved-world evidence supplies that provenance.

## Failure classification

`ACCOUNTING_THREE_OF_FOUR` requires all of the following after the full
observation window:

1. The shared destination contains the four-wheat stack and all four source
   chests have no wheat remaining.
2. Outstanding source claims are zero.
3. Both task-audit reads, bracketing the physical probes, report `done=3` and
   `assigned=1`.

Other physical/task/history discrepancies are retained as
`TASK_ACCOUNTING_MISMATCH`. Other assertion failures, infrastructure failures,
invalid evidence, and missing planned results have separate statuses. A
failure cannot be promoted to a pass because the items arrived. The original
fixture must complete successfully and the additional terminal witnesses
must agree before a trial is `PASS`.

These terminal reads are not an atomic Minecraft snapshot. Reconciliation
during the probes is visible in the two audits. A transient discrepancy that
resolves before these probes remains in the original failed fixture/logs, but
does not count as the stable terminal three-of-four signature. The reported
frequency therefore describes this operational detection rule, not every
possible transient accounting lag.

## Denominators and uncertainty

Every declared trial remains in the summary. A boot failure, missing artifact,
partial fixture, missing persisted identity, or malformed evidence is an
**unknown accounting outcome**, never a silent zero. Duplicate trial records,
mixed revisions, and mixed protocol hashes invalidate pooling. Reused world
UUIDs cannot count as additional independent observations.

The report shows the number of observed three-of-four events, assessable
worlds, unknown worlds, all five planned worlds, and all outcome categories.
The descriptive event frequency and 95% Wilson interval use only assessable
worlds. Separate bounds over the entire planned cohort show the effect if
none or all of the unknown worlds had the accounting event. These missingness
bounds are not a confidence interval.

For example, **zero events in five assessable worlds still has an approximate
95% Wilson upper bound of 43.4%** under an independent-comparable-trials
assumption. Five passing worlds are useful validation of this revision, but
cannot resolve the earlier reliability concern or precisely estimate a rare
failure probability. Preserve the pilot before predeclaring a larger cohort;
do not rerun until a favorable result replaces a failed trial.

## Running and reading the pilot

GitHub Actions runs the full cohort for relevant PR changes or via
`workflow_dispatch`. The `colony-reliability-summary` artifact contains the
pooled JSON report. Individual `colony-reliability-world-XX` artifacts contain
the logs and `trial-result.json`, including failed attempts.

In a fresh disposable checkout with Java 17 and Gradle 8.8, one declared trial
can also be run explicitly:

```bash
python3 scripts/run_colony_reliability_trial.py --trial-id world-01 --seed 43101 --output reliability/world-01
```

The runner refuses an existing `run/server.properties`; use a fresh checkout
for each world. It deliberately does not overwrite a player's server setup.
The runner returns nonzero for a failed trial. The summary also returns
nonzero unless every required trial passes, while writing its report first.

```bash
python3 scripts/summarize_colony_reliability.py downloaded-artifacts --expected-commit COMMIT_SHA --output colony-reliability-summary.json
```

`python3 -m unittest discover -s scripts -p 'test_colony_reliability.py'`
verifies false-pass rejection, failed/missing denominators, duplicate worlds,
revision and seed mismatches, interval behavior, and actual binary NBT parsing.
Those unit cases are synthetic test inputs and are never reported as live
Minecraft trials.

## Additional accounting event in v0.10

The original three-of-four event remains frozen. The subsequent evaluator
also reports `physical_delivery_accounting_event`: four physical deliveries,
zero claims, and stable, plausible terminal task counts with `done<4` and
`assigned>0`, after the full observation window. It has separate uncertainty
and unknown-trial accounting. This captures the two-complete/two-assigned
variant observed in the #212 cohort without redefining the original event.
See [delivery reconciliation v0.10](COLONY_DELIVERY_RECONCILIATION_V0_10.md)
for the retained baseline evidence, exact scope, and regression design.
