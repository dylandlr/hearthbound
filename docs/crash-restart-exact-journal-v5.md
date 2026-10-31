# Crash-restart acceptance v5: exact attempt identity

The disposable crash workflow now captures the operation UUID logged by the actual post-write-ahead hard-halt hook and passes it into the second Minecraft JVM through `HEARTHBOUND_CRASH_OPERATION`.

The second-JVM recovery probe now opens the checksum-validated `DurableOperationIntents` record for that precise operation and verifies the stored operation UUID and `wheat=1` payload. This fails if a previous baseline GameTest's unrelated surviving journal was the only evidence. CI now demands `HEARTHBOUND_CRASH_RESTART_EXACT_ATTEMPT_PASS` naming the specific crashed operation. Filename hashing in the first process remains a separate evidence check.

This still does **not** establish safe crash reconciliation, nor prove the citizen and Create machine inventories survived consistently. The isolated destructive workflow remains manual-only, and commit-triggered Forge checks do not execute it. The next stage needs a second-process comparison with persisted entity and Create inventories plus a world that can reliably run the interrupted task on a freshly saved baseline.
