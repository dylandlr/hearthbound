# Isolated citizen hard-crash hook v1

The citizen milling controller now contains a deliberately disabled-by-default hard-crash hook **after** `CitizenSupplyAttempt.begin` fsyncs the write-ahead attempt and **before** the Create inventory mutation.

Activation requires BOTH environment variables on the disposable Minecraft server JVM:

```sh
HEARTHBOUND_FAULT_TEST_ACK=isolated-citizen-crash-test
HEARTHBOUND_CITIZEN_CRASH_STAGE=after_attempt_before_mutation
```

When activated for the first authorized delivery, the server logs `HEARTHBOUND_FAULT_INJECTION_AFTER_ATTEMPT` and calls `Runtime.halt(86)`, intentionally skipping JVM shutdown hooks and normal world saves. **Never use these variables in production or the ordinary acceptance world.**

This commit adds a genuine controlled process-exit boundary in the runtime, **not yet an end-to-end crash/restart acceptance run**. A separate disposable-world workflow must first create a stable baseline world and citizen task, start the server with these variables, verify the expected exit 86 and persisted attempt, restart without these variables, and independently check wheat counts and no replay. An abrupt halt may lose earlier unsaved entity changes; classify any discrepancy as ambiguous rather than synthesizing state or authorizing another transfer.
