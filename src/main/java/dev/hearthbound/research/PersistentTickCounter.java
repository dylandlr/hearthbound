package dev.hearthbound.research;
public final class PersistentTickCounter {
    private long tick;
    public PersistentTickCounter(long restoredTick) {
        if (restoredTick < 0) throw new IllegalArgumentException("Negative saved tick");
        tick = restoredTick;
    }
    public synchronized long advance() { tick = Math.addExact(tick, 1); return tick; }
    public synchronized long current() { return tick; }
}