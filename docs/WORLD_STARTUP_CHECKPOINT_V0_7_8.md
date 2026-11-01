# v0.7.8 World startup checkpoint

Disk-backed independent marker with fail-closed startup states. Initial marker creation returns RESTART_REQUIRED, not READY. Caller must supply UUID loaded from persistent Minecraft SavedData and independently verify journal ownership and rollback state. Neither is implemented by this component. A marker is not proof of atomic Minecraft SavedData persistence. On symlink/invalid file/disk error fail closed. Check directory fsync support on deployment OS. Run the pure Java test under Java 17; actual Forge server integration is pending.
