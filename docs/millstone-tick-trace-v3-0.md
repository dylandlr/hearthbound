# Hearthbound v3.0 — Server-tick millstone telemetry

Added an operator-only bounded trace to sample an existing Create millstone at server END tick:

- `/hearthbound millstone trace start <x> <y> <z> <ticks>` where `ticks` is 1..1200.
- `/hearthbound millstone trace stop` prints sample count and the last 20 inventory observations.

Trace data remains in memory, limited to one monitored millstone, and does not award rewards or discover recipes. A matching world/dimension and loaded chunk are required. It is a **diagnostic** to correlate Forge tick timing with any exposed item-handler slots, not a reliable account of consumed items. A Create millstone may not expose its internal processing items through the generic item capability, so an empty report is not proof of no processing.

The new commands and tick listener require fresh Forge compilation and live testing. They are not yet verified in Minecraft. The standing EULA-gated dedicated-server smoke workflow remains unexecuted.

## Manual validation

1. Launch an EULA-accepted Forge 1.20.1 development server with Create and Hearthbound installed.
2. Confirm `/hearthbound status` says `Create=loaded`.
3. Place and power a millstone; inspect its loaded block position.
4. Start the trace for 200 ticks, insert wheat, and after the processing window stop the trace.
5. Capture trace and server logs for comparison against Create's actual recipe execution path.
6. Do not feed snapshots to `MillstoneReceiptGate` as `InputProof`: reward credit still requires trustworthy mutation-time input and output evidence, persisted with an operation UUID.

Follow-on work: an authoritative Create recipe mutation hook, persisted event journal, and dedicated server GameTest.
