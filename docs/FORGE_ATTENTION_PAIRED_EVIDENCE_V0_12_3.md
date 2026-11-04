# Hearthbound v0.12.3 — Linked attention choice/outcome evidence

Experimental stack on PR #143. This milestone adds a **bounded append-only server-session outcome journal** to existing Forge attention opportunities. It is not a persistent all-session recorder, neural policy, autonomous explorer, or task executor.

## Timing and identity

On every scripted citizen inspection attempt (at most one per observer per five ticks), the server records an ATTENTION_OPPORTUNITY *before* source inspection. The journal then appends exactly one ATTENTION_OUTCOME with the same server tick, observer UUID, dimension and selected coordinates. Outcomes are:

- `OBSERVED`: source sensor produced a verified EMPTY or AVAILABLE state with measured wheat quantity; evidence is `REAL_FORGE_SOURCE_OBSERVATION`.
- `UNOBSERVED / CHUNK_UNLOADED`: the selected source chunk was not loaded.
- `UNOBSERVED / OBSERVER_UNAVAILABLE`: citizen was missing, dead or no longer marked.
- `UNOBSERVED / SENSOR_UNKNOWN`: selected source failed the sensor's legitimacy or inventory checks.

Unobserved outcomes always use `state=UNKNOWN wheat=-1 evidence=NO_VALID_OBSERVATION`; the validator maps unknown quantity to JSON null, never zero. A choice can fail and still consume the inspection budget.

## API and retention

- `/hearthbound citizen_outcome_latest`: one latest outcome for reliable RCON polling
- `/hearthbound citizen_outcomes`: bounded session journal inspection, permission level 2

The in-memory ring retains the latest 128 outcomes per level; it is not a complete longitudinal log. All operations remain read-only and every record explicitly says `action_authorized=false`.

## Acceptance

The dedicated Forge RCON test registers two chests for one citizen, polls the latest opportunity and outcome independently, and saves the pair **only if their identity fields match**. The paired validator rejects unmatched tick, observer, dimension or selected source, invalid state/quantity combinations, unauthenticated or leaked alternative-source fields, and execution authority. It emits `real-attention-paired-evidence.json` with unselected options recorded as UNKNOWN and no counterfactual reward.

Unit tests cover observed and unobserved cases, forged data rejection, cross-citizen mismatches and source mismatch. Both SCRIPTED and TRAINED_MLP dedicated-server arms run the test and archive exact captured records.

## Research boundaries

This records the scripted scheduler's decisions, **not** a learned attention policy. No outcome for an unselected candidate can be inferred. Matching by tick/observer/source is valid here because the sampler limits each citizen to one choice per five-tick interval. For long-lived experiments, add run/session IDs, monotonically increasing event sequence numbers, durable append-only server logs, checksums and recovery checks; a 128-entry ring is insufficient for training datasets. A later replay model must use only knowledge available at the decision timestamp.
