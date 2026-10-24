# Durable pre-operation intents

DurableOperationIntents is a storage prototype for stable milling operation IDs. It is not connected to the live Create hook yet.

The caller supplies a stable machine key (world identity, dimension, position and machine incarnation) and deterministic full pre-operation evidence. The store generates an operation UUID, writes the UUID/key/evidence plus checksum to a staging file, forces it, atomically publishes it, then forces the directory before returning newlyCreated=true.

A matching retry returns the same UUID and evidence with newlyCreated=false. This flag is essential: finding an unresolved intent does NOT authorize replaying a machine mutation. The caller must reconcile machine state first. Changed evidence for the same machine key is rejected, preserving the original intent.

There is deliberately no complete/delete method. Retiring the intent safely requires establishing that the corresponding machine checkpoint and outcome are durable. Without that coordination, issuing another operation ID could reward a replay of a pre-crash input. Wiring this store directly into the current hook would therefore leave machines blocked after their first attempt; that integration is deferred until reconciliation exists.

A process lock serializes preparation. Same-JVM callers should share one store instance; overlapping file locks from separate instances can throw. Missing files differ from unreadable/corrupt/truncated files; the latter block preparation. The full evidence is retained, not only its hash. The caller remains responsible for canonical serialization and authoritative evidence.

Tests terminate child JVMs after staging, publication, and directory force. Unpublished staging does not authorize processing; published intents reload with the same UUID and require reconciliation. Two concurrent writer JVMs must receive the same UUID. Additional cases check changed evidence, different machine incarnations, full snapshot reload, checksum corruption and truncation.

Assumptions: an existing directory on a local filesystem supporting file locks, atomic rename and directory force. The tests cover abrupt process termination, not power failure. Leftover staging files are ignored but not automatically removed. File deletion, old backups and machine-key reuse need external recovery policies. Live research rewards remain disabled.
