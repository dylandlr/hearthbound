# Durable credit ledger prototype

DurableCreditLedger stores operation ID, beneficiary, reward amount and a caller-supplied canonical receipt together in one versioned, SHA-256-checked frame. Balances are derived from committed frames; there is no separate balance file that can diverge from the receipt ledger.

A process lock covers the read/check/append/force sequence. Matching retries return false without adding a reward. Any difference in beneficiary, amount or receipt for the same operation ID is rejected. Separate JVMs serialize their writes. Multiple instances in the same JVM may fail with an overlapping-lock exception; use one shared instance there.

The writer forces the parent directory, appends the complete frame, then forces the data file before acknowledging success. A failure after a complete write but before acknowledgement is an uncertain result: retry the SAME operation ID and receipt. Never generate a replacement ID. A duplicate retry also forces the file before returning.

An incomplete frame, invalid version, duplicate persisted ID, or checksum mismatch blocks every balance read and commit. No automatic truncation or replay occurs. This deliberately sacrifices availability until explicit reconciliation. Missing files start an empty ledger; detecting deletion or restoration of an older valid ledger requires an external checkpoint and is not implemented. The file is scanned in full for each operation; this prototype is not a scalable database.

The standalone suite launches three writer JVMs that terminate via Runtime.halt after the header, after the payload, and after force. Torn writes block access; a forced write survives and a retry does not double credit. Two additional concurrent JVMs attempt the same credit. Tests also cover conflicting retries, checksum corruption and reward overflow. These test process termination on CI's filesystem, not power failure or storage-controller guarantees.

The directory must already exist on a local filesystem supporting Java file locks and directory force. Unsupported durability operations fail; no fallback silently weakens the write protocol.

This is a storage component, not a live reward integration. Callers must supply validated durable operation evidence and a deterministic full receipt representation. The current live milling observation UUID and item-ID-only receipt gate are insufficient. Durable pre-operation identity, full item-NBT-aware receipt integration, machine-state reconciliation and a quarantine repair procedure remain required. Live research rewards remain disabled.
