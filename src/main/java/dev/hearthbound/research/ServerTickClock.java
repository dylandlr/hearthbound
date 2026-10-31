package dev.hearthbound.research;

/** In-memory server-lifecycle clock. The logical server supplies tick observations. */
public final class ServerTickClock {
    private long logicalTick;
    private long lastServerTick = -1;
    private boolean initialized;
    public ServerTickClock(long recoveredLogicalTick) {
        if (recoveredLogicalTick < 0) throw new IllegalArgumentException("negative restored clock");
        this.logicalTick = recoveredLogicalTick;
    }
    public synchronized long observe(long serverTick) {
        if (serverTick < 0) throw new IllegalArgumentException("negative server tick");
        if (!initialized) { initialized = true; lastServerTick = serverTick; return logicalTick; }
        if (serverTick < lastServerTick) throw new IllegalArgumentException("server tick regressed in session");
        if (serverTick > lastServerTick) {
            logicalTick = Math.addExact(logicalTick, serverTick - lastServerTick);
            lastServerTick = serverTick;
        }
        return logicalTick;
    }
    public synchronized long current() { return logicalTick; }
}
