# First Mill v4.8 — post-admission contamination quarantine

## Baseline
At commit `a01ebc38`, Forge Create integration, powered milling, Sable's physical hauling and direct processing receipt, and the receipt/reservation restart regression **all passed**.

## Added
`MillReservations` now tracks an irreversible, persisted `tainted` job UUID set. `preDeliveryClean` enforces that the matching reserved Create millstone still has empty input and output inventories at two task boundaries: immediately before wheat extraction from the source chest, and immediately before carried wheat insertion into the destination.

Unexpected physical contents mark the experiment tainted, persist the marker, and prevent the matching receipt from being accepted. At pickup the job pauses without extracting wheat; at delivery the cargo is quarantined rather than silently inserted or destroyed. The machine reservation is **not released automatically** after a taint and the taint is not cleared when items are removed.

## Regression
The Sable gameplay test reserves a newly cleaned millstone for a second citizen, then uses an explicit operator test fixture to add flour *after reservation* but *before the pickup step*. It asserts the haul status signals contamination, the mill reservation is TAINTED, the second job gets no process receipt, and removing that flour does not clear the taint.

## Remaining risk
This is boundary-time contamination detection, not continuous physical machine access control. A hostile input can enter and process between checks; inventory may be altered after authorized insertion. No discovery, XP, Outcome Ledger reward or colony credit is issued. Further work should track live input access and provenance at Create's item handler boundary, and test after-delivery adulteration. Do not describe this as complete physical isolation.

The v4.8 CI results must be checked before treating these new guards as validated.
