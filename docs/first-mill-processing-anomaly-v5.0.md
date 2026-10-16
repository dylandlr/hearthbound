# First Mill v5.0 — processing-time anomaly invalidation

## Passing baseline
Commit `2ada669f` passed all four Minecraft CI workflows, including post-reservation pre-delivery contamination detection. Later authorized insertion changes (v4.9) are checked separately in CI.

## Change
The direct Create `MillstoneBlockEntity.process()` callback now permanently taints a held Hearthbound experiment if the processing inventory state violates the exact authorized-one-wheat contract: one wheat before, zero wheat after, zero pre-existing flour, and increased flour afterward. A *second* processing operation for the same job also taints it rather than merely being ignored as a replay.

`MillProcessReceipts.hasReceipt` refuses tainted jobs, even if a direct callback receipt had previously been recorded. The read-only `/sable mill-process <job-uuid>` response becomes `MILL_PROCESS INVALIDATED ... NO_RESEARCH_CREDIT`. The persistent reservation audit shows `MILL_RESERVATION TAINTED`.

## New actual-Minecraft adversarial regression
A test fixture creates a separate Create millstone **without kinetic power**. A third Sable hauls one wheat and successfully inserts it. Then the fixture replaces the mill's input inventory with two wheat **after the authorized delivery** but **before processing**. Power is then applied to cause Create's real processing method to execute. The experiment must become tainted and the job must not retain a process receipt.

## Limitations
This detects extra or unexpected quantities when the direct callback fires. It cannot detect a malicious one-for-one replacement with identical wheat, or external inventory mutation that occurs entirely between observation boundaries and leaves the same state. It is not complete item provenance or physical machine isolation. Never issue personal research XP, technology unlocks, teaching credit, or colony reward from this receipt layer alone.

The new regression and all existing Minecraft workflows must pass on this revision before these guards can be treated as verified.
