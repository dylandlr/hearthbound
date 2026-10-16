# First Mill v4.9 — authorized insertion snapshot

## Passing baseline
Commit `2ada669f` passed Forge integration, powered Create milling, the full Sable physical-hauling gameplay regression, and persistent receipt/restart checks.

## New server-side evidence contract
After an actual successful Sable one-wheat inventory insertion, `MillExperimentTrace.deliveryComplete` inspects the Create millstone immediately. It records `authorizedInputCount=1` and `authorizedTick` only if the machine contains exactly one wheat and its output flour count equals the recorded pre-insertion baseline. A mismatch permanently marks the current job tainted.

The direct `MillstoneBlockEntity.process()` callback now requires **one wheat before and zero after**, **zero flour before**, increased flour afterward, and an exact authorized insertion snapshot with a matching recent citizen job and persistent mill reservation. Observations are exposed through the read-only `/sable mill-trace` command. The physical First Mill RCON test asserts this insertion evidence.

This links an authorized item transfer to a Create processing callback more tightly than matching a nearby villager. It does not block or identify a malicious replacement with identical wheat between insertion and processing, nor does it prevent other Create, hopper or player operations. It is **not** full physical access control or item-instance provenance.

## No learning credit
Receipt storage is still for experimental and auditing use only. Recipe unlocks, social learning rewards, individual/civic credit and Outcome Ledger payouts stay disabled. The new server CI must pass before v4.9 is considered verified.
