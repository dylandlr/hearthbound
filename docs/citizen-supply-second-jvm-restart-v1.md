# Citizen milling delivery second-JVM restart acceptance

A successful real Minecraft citizen supply GameTest now writes `citizen-supply-restart-expected.nbt` with the stable citizen UUID, durable operation UUID, target machine position, and dimension. The GameTest then reassigns a blocked delivery into the occupied Create input and retains that unresolved task.

A separate Forge `runServer` JVM boots the saved GameTest world and checks that the same citizen work-order operation and write-ahead attempt can be recovered and that the blocked `MILL_SUPPLY` task remains in the persisted citizen registry. CI requires `HEARTHBOUND_CITIZEN_SUPPLY_RESTART_PASS` and captures the expectation file.

This establishes cross-process survival of the attempt and outstanding task. It **does not** yet reload and compare the actual villager's item counter and Create millstone inventory after restart, and it does not reconcile or retire attempts. Forensic receipt validation across all persisted stores remains necessary before claiming crash-safe exactly-once semantics.
