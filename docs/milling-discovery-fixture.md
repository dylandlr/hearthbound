# End-to-end milling discovery credit fixture

The motor GameTest now connects a durable pre-operation intent, real Create processing, the persisted observation, a saved machine checkpoint and an isolated durable credit ledger. It checks full input/output NBT agreement, one consumed wheat, the selected wheat milling recipe, positive output evidence and checkpointed outputs before crediting one point.

The receipt contains the operation ID, machine key, discovery recipe, full before-state and full observation. Its exact serialized representation is retained for retry. A second Minecraft process reloads the machine and intent, compares the observation/receipt, confirms a balance of one, rejects an identical retry without another credit, and rejects a conflicting reward amount without changing the balance.

This is fixture-only credit for a fixed synthetic beneficiary, stored under hearthbound-fixture-credits. It is not an autonomous citizen, recipe unlock UI, or production reward integration. The live audit still reports researchCredit=false. Its fixture operation identity is associated through controlled test sequencing, not a production pre/post-processing adapter.

The machine checkpoint precedes credit, but real crashes between those writes and production intent retirement remain unhandled. No exactly-once claim applies to arbitrary live machines. This fixture proves one controlled clean-save/restart path.

CI requires HEARTHBOUND_DISCOVERY_RESTART_PASS. In explicit restart-check mode the server shuts down cleanly after all assertions; timeout now fails instead of serving as the normal smoke-test ending.
