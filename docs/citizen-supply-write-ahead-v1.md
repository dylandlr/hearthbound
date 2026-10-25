# Citizen supply write-ahead attempt v1

The existing Minecraft citizen millstone task now records an on-disk, checksummed delivery attempt keyed by the recovered durable work-order operation ID **before** moving wheat into Create's inventory. If an attempt is already present, or the attempt journal cannot be read safely, the server refuses to repeat the mutation. The GameTest asserts that the attempt exists after the completed live delivery.

This is intentionally conservative. A crash after writing the attempt but before the machine mutation can strand the task, because the evidence is ambiguous. The attempt journal currently has no retirement mechanism; later assignments to the same unresolved citizen/machine operation are blocked even if the machine becomes empty. An explicit reconciler with proof from citizen NBT, Create machine state and persisted receipts is the next prerequisite.

This is **not** yet exactly-once crash recovery, nor a fully autonomous milling process. Only the first wheat delivery is currently automated; power activation, processing, flour collection and distributed transaction reconciliation remain outside this milestone.
