# Hearthbound v0.16.3 — Frozen neural report → physical Minecraft haul

## Experimental question

Can a real Hearthbound executor use a report **delivered by a different real citizen** to select an executable task with a frozen, simulator-trained MLP, then physically move a Minecraft item to the selected destination?

The test is **operator-triggered**, not autonomous task initiation or colony self-government. It makes the selected task executable rather than merely displaying a shadow prediction. No claims of generalization, improved productivity or learned cooperation are valid from one successful run.

## Actual roles

- **Source scout:** a separately spawned, marked Forge villager. The scout personally observes chest A and B, then shares those observations through the existing `CitizenKnowledgeExchange.share`, which validates source evidence, identities, physical communication distance and freshness.
- **Recipient and executor:** Sable. She initially has **no direct memory** of either chest. The other citizen's reports are stored in Sable's *recipient-owned* memory, not promoted to direct observations.
- **Policy:** the same SHA-pinned 10→16→3 simulator-trained MLP used in v0.16.2. It sees only recipient-delivered report features and an explicit two-source candidate menu.
- **Operator:** defines the trial, candidate source positions and destination, and triggers one decision; does **not** choose the winning source or modify inventories to fake a transfer.

## Commands

```text
/hearthbound-share-direct <source> <scout> <recipient>
/hearthbound-report-dispatch <executor> <source-a> <source-b> <destination> <exposed|withheld>
/hearthbound-report-execution <executor> <job-uuid>
```

All are restricted to permission-2 operators. The physical executor is also the report recipient; this prevents a remote recipient's memory from silently controlling someone else's work.

The dispatch command calls the **same typed, pre-action MLP evaluator** as the frozen shadow probe. `WITHHELD` reads no recipient reports, returns `ABSTAIN` and creates no job. `EXPOSED` can choose a source only when an admissible report exists. A selected source must belong to the supplied menu. Only after selection does the bridge check loaded chunks and call the existing `SableHauling.assign`. No inventory read is used as an MLP feature. The existing motor is the sole authority that can pick up and deposit wheat.

Upon assignment, the bridge persists the minted hauling UUID, world UUID, actual executor/recipient UUID, candidate set, selected source, destination, decision tick, assignment tick, report ID, model SHA-256, policy version, and explicit operator-triggered origin on the executor's real villager NBT.

The read-only execution probe verifies that this receipt agrees with the **same job's** real completed `SableHauling` assignment. Crucially, it labels `inventory_delta_verified=false`: completion NBT is evidence about the motor's state, but not by itself independent proof of an observed physical transfer.

## Independent real-world acceptance

The GitHub Actions `real-neural-report-haul.yml` first regenerates and verifies the frozen model and Python/Java numerical parity **before starting Forge**. Then `scripts/rcon_neural_report_haul.py` executes a physical-world test:

1. Set up a flat disposable Minecraft world with a chest containing 3 wheat (A), another with 1 wheat (B), and an empty destination chest.
2. Spawn the actual scout and Sable. Confirm that Sable lacks direct observation of both sources.
3. Before communication, verify the exposed policy abstains, with no hauling assignment. After communication, verify the withheld policy also abstains and inventory is unchanged.
4. Have the scout directly observe actual chest contents and explicitly transmit reports to Sable. Verify the reports remain secondhand in Sable's memory.
5. The frozen MLP selects A. The dispatch command creates a new real hauling job **for A**; the output binds the pre-action report and model SHA to the executor UUID, task and source. The operator never inserts a synthetic item.
6. Wait for Sable's actual server-side pickup and delivery. Require the real completion receipt and separately read **all three** actual chest inventories: A must change 3→2, B must remain 1, destination must change 0→1.
7. Require no rewards, no learning updates, no research credit, no model changes, and no claim of spontaneous autonomy.

This is a single physical acceptance, not a statistical A/B comparison. The outstanding intermittent navigation bug ([issue #181](https://github.com/dylandlr/hearthbound/issues/181)) is **not waived** by this milestone; a stuck physical job must fail with read-only diagnostics, not be counted as success.

## Research interpretation

Successfully delivering the selected source's wheat would establish the chain **real scout observation → explicit local communication → frozen neural decision owned by executor → actual Minecraft hauling → independent physical inventory evidence**.

It would **not** establish that Sable autonomously initiated the task, that simulation-supervised neural learning outperforms scripted decision-making on real Minecraft worlds, that a recipe was discovered, or that the scout deserves a quantified cooperative reward. Those are the next controlled experiments.

The next milestone should run multiple random-order, matched-seed `SCRIPTED` vs `FROZEN_MLP` trials including abstention, stale reports, failure recovery, adversarial inventories and real navigation, with confidence intervals and physical execution receipts on every counted success.
