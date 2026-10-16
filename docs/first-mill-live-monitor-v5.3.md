# First Mill v5.3 — server-tick authorization monitor

## Last green baseline
Commit `c0126177` passed all four Minecraft CI workflows (Create integration, powered milling, Sable end-to-end tamper test, SavedData restart).

## Implementation
Once Sable has inserted exactly one wheat and her machine observation has recorded `authorizedInputCount=1`, `MillExperimentTrace.monitorAuthorizedInput` inspects the loaded Create millstone on **each Sable server tick**, until a direct processing callback receipt is recorded.

While the reservation still belongs to that citizen, the machine must contain exactly one wheat input, no other input stacks, and an empty output inventory. Any unexpected state permanently taints the held experiment in SavedData. The method does not load distant chunks. Once the Create callback records an outcome, this pre-processing monitor stops and the direct callback/release safety contracts apply.

The v5.3 RCON regression injects a second wheat **after** the authorized delivery but **before** the previously unpowered millstone gets a motor. The test requires the reservation to become TAINTED during this powerless interval. On powering the mill, the separate process-entry Mixin must still preserve both wheat and keep the receipt INVALIDATED.

## Limitations
This increases temporal coverage but is still sampling, not interception of every inventory mutation. An identical one-for-one item substitution between ticks is not detectable, nor can arbitrary modded code that directly edits Create internals be blocked. This is not physical inventory exclusivity, identity tracking, automatic scientific discovery, or a reward contract. Knowledge and rewards remain disabled.

Updated v5.3 CI must pass before the monitor is treated as validated.
