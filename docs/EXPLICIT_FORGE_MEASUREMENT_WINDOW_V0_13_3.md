# Hearthbound v0.13.3 — Explicit Forge intervention measurement cutoff

## Motivation

The first four-arm real Forge experiment (PR #153, run 41765308264) passed its CI and archived a matched seeded-arm report. For both the SCRIPTED and TRAINED_MLP trial labels, **5 of 6** operator resource interventions had a subsequently observed matching selected-source state (reported coverage 0.833333). Both arms used the same scripted citizen attention sampler and the identical configured seed `hearthbound-resource-probe-A`; this is **not** evidence that an MLP controlled or improved attention.

The original v0.13.1 coverage auditor bounded the final intervention's observation window by the last intervention's own recorded tick when no later same-source mutation appeared. This can *systematically omit* subsequent valid observations. Conversely, blindly examining the whole sealed journal after the scheduled experiment would contaminate the measure with observations made during fixture cleanup.

## Change

The real RCON seeded experiment now waits approximately one full scripted sampling cycle following its sixth resource intervention, queries `time query gametime`, and records a strictly later `measurement_stop_tick` **before any chest is restored**. Schedule validation rejects any cutoff that does not follow the last verified mutation.

The observation-coverage auditor now requires observations to be strictly after the relevant mutation's recorded `tick_after`, and strictly before the next same-source mutation or the recorded measurement cutoff. Equality with either boundary is excluded as ambiguous. For older intervention records without the cutoff, the legacy conservative final boundary remains, and the report explicitly labels the absence.

The seeded-arm comparison contract now requires the explicit cutoff in both arms. Tests verify that a final intervention can be witnessed after its mutation and before the cutoff, while a post-cleanup observation cannot inflate coverage.

## Interpretation and tests

This change **does not retroactively modify** the original 5/6 results or imply which specific intervention was missed. It improves the measurement protocol for future live runs. Once the corrected experiment is verified in real Forge CI, compare the new report to the old, noting that the observation window has changed. The recorder still contains only source selections and directly observed results; all unselected alternatives and counterfactual rewards remain unknown.

No learned attention controller or new citizen task authority is introduced. Both fixed baseline and seeded research test arms remain isolated.
