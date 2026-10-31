# Isolated crash evidence identity hardening

The manually dispatched disposable-world crash test now snapshots the exact set of write-ahead attempt filenames from its clean saved baseline. After the hard termination it requires **exactly one newly persisted attempt**, rather than merely finding an attempt left over from baseline GameTests.

It also extracts the injected operation UUID from the JVM crash marker and computes the expected SHA-256-derived intent filename from `supply-attempt/<operation-uuid>`. The sole new persisted attempt must match that file name. Both before/after inventories of filenames are uploaded as evidence.

This prevents a false positive in which unrelated existing journals satisfy the crash condition. The experiment remains unexecuted as a manual-only workflow; it does not yet prove that full entity and Create inventories are crash-atomic. The second-JVM phase currently inspects journal survival only.
