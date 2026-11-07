# Hearthbound v0.16.1 — Report-conditioned source-choice experiment

## Question

Does exposing an independent citizen's delivered source report to a **read-only action-selection policy** change its choice, when the physical world, two candidate sources, and recipient identity are unchanged?

This is a controlled *information-dependency* experiment. It does not establish machine learning, autonomous communication, physical delivery gains, or an emergent research breakthrough.

## Implemented observation contract

`ReportConditionedChoice` is an intentionally simple deterministic, scripted baseline:

- The choice menu is supplied before the source-specific report lookup; it contains two distinct source coordinates.
- Each candidate may have a recipient-owned `CitizenKnowledgeExchange` report originated from another marked citizen's **actual direct Forge chest observation**.
- Only reports with the correct recipient, sender, origin, fresh delivery time, source revision, and `AVAILABLE`/positive-wheat content enter this policy.
- `WITHHELD` does not even read the reports in the world bridge; it must `ABSTAIN` even if the recipient possesses a report.
- `EXPOSED` chooses the highest *reported* wheat, with a deterministic source-key tie-breaker. No world inventory is sampled during the policy decision.
- `EMPTY` reports supersede an older `AVAILABLE` report for the same source; stale reports are not silently upgraded to ground truth.
- Every decision is `task_authorized=false reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT`.

The permission-2 operator command (read-only) is:

```text
/hearthbound-report-choice <recipient> <first-source> <second-source> <exposed|withheld>
```

It does not execute or schedule work, move citizens, access block inventories, mutate reports, or train models. It produces a decision that can be compared against the **same** observed Minecraft menu and world state, but is not itself an executor action.

## Real Forge experiment

`.github/workflows/real-report-choice-experiment.yml` boots a disposable real Forge server and executes `scripts/rcon_report_choice_experiment.py`. Its operator-only oracle and policy evidence are kept separate.

1. Set a real chest A to three wheat and chest B to one wheat. Spawn a real sender Sable and a different marked recipient, with no shared reports.
2. Confirm **both** exposed and withheld policies abstain before communication.
3. Sable directly observes both physical inventories and explicitly communicates the reports to the recipient. Confirm recipient-only memory of reports.
4. With no changes to inventories or candidate set, evaluate **WITHHELD** and **EXPOSED**. Require the former to abstain and the latter to select A.
5. Change the physical inventory of A to empty **without notifying the recipient**. Exposed must still choose A, demonstrating that the policy is not secretly consulting the real chest.
6. Have the sender directly observe the empty A and share the new report. Exposed must now choose B while withheld still abstains.
7. Verify the real chests and archive RCON/Forge logs plus structured result receipts.

A new Java 17 unit suite covers choice determinism, freshness, replay, wrong recipient, hearsay, self-report, future ticks, invalid candidate menus, and no world-inventory access.

## Interpretation and next experiments

An observed `EXPOSED` versus `WITHHELD` decision difference is a designed **software-level information-dependency effect**. Because the policy is explicitly programmed to use reports, this is *not* a learned effect or evidence of emergent teamwork. It demonstrates a clean experimental condition for the later MLP/recurrent policy arms.

Next: connect the same immutable candidate menus and source-report features to an MLP trained **only in a fast simulator**, freeze the model and compare out-of-seed accuracy, abstention calibration, decision latency and real Forge physical task success under exposed/withheld arms. Pre-register worlds, seeds, observation timestamps, source arrival/hauling metrics, and confidence intervals. Avoid labeling unexecuted source choices as successful deliveries.

The existing v0.15.9 crash/rollback evidence gate and v0.16.0 direct-witness source protection remain separate boundaries. No numeric contribution shares, recipe unlocks, research reward or autonomous learning is introduced by this milestone.
