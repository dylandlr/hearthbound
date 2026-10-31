# Hearthbound v3.1 — bounded millstone trace lifecycle

The `/hearthbound millstone trace status` subcommand now reports an active trace's sample count and capacity. The collector automatically closes the trace at its configured maximum and retains the final report for one subsequent `trace stop` command. `trace start` begins a new trace, replacing a completed report.

Manual checks after EULA-authorized server startup:
1. `/hearthbound millstone trace start <x> <y> <z> 3`
2. `/hearthbound millstone trace status` should initially show 0/3.
3. After at least three server END ticks, `trace status` should say completed.
4. `trace stop` returns up to the last 20 samples, and a second `stop` returns none.
5. Start another trace immediately; should not be blocked by the previous completed trace.

The collector only samples exposed Forge item-handler slots and does not establish a consumption or production receipt. Its samples are in-memory and not persisted to disk. Forge compilation and live command validation are required before calling this feature tested.
