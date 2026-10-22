package dev.hearthbound.research;

import java.util.*;

/** Server-thread-owned deterministic sequencing. Not itself a persistent journal. */
public final class ServerTickEventLedger {
    public record Event(long tick, int ordinal, UUID operationId, String kind, String worldId,
                        String dimension, String machinePosition, String recipeId) {}
    private final List<Event> events = new ArrayList<>();
    private final Set<String> unique = new HashSet<>();
    private long lastTick = -1;
    private int nextOrdinal = 0;

    public synchronized Event record(long tick, UUID operationId, String kind, String worldId,
                                     String dimension, String machinePosition, String recipeId) {
        if (tick < 0 || tick < lastTick) throw new IllegalArgumentException("Regressing server tick");
        Objects.requireNonNull(operationId);
        for (String s : List.of(kind, worldId, dimension, machinePosition, recipeId))
            if (s.isBlank()) throw new IllegalArgumentException("Missing event provenance");
        String key = operationId + "/" + kind;
        if (unique.contains(key)) throw new IllegalArgumentException("Duplicate event kind for operation");
        if (tick > lastTick) {lastTick = tick; nextOrdinal = 0;}
        if (nextOrdinal == Integer.MAX_VALUE) throw new IllegalStateException("Ordinal overflow");
        Event event = new Event(tick, nextOrdinal++, operationId, kind, worldId, dimension, machinePosition, recipeId);
        unique.add(key);
        events.add(event);
        return event;
    }
    public synchronized List<Event> snapshot() { return List.copyOf(events); }
    public synchronized void restore(List<Event> restored) {
        if (!events.isEmpty()) throw new IllegalStateException("Restore before accepting events");
        long tick = -1; int ordinal = -1;
        for (Event e : restored) {
            if (e.tick() < tick || (e.tick() == tick && e.ordinal() <= ordinal) || e.tick() < 0)
                throw new IllegalArgumentException("Unordered recovered journal");
            String key=e.operationId()+"/"+e.kind();
            if (!unique.add(key)) throw new IllegalArgumentException("Duplicate restored event");
            events.add(e); tick=e.tick(); ordinal=e.ordinal();
        }
        lastTick=tick; nextOrdinal=ordinal+1;
    }
    private ServerTickEventLedger() {}
}
