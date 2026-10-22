package dev.hearthbound.integration;
import dev.hearthbound.research.PersistentTickCounter;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.saveddata.SavedData;
/** Stored in the overworld so all dimensions share a clock. */
public final class HearthboundClockSavedData extends SavedData {
    private static final String KEY = "hearthbound_server_clock_v1";
    private final PersistentTickCounter clock;
    public HearthboundClockSavedData() { this(0); }
    private HearthboundClockSavedData(long tick) { clock = new PersistentTickCounter(tick); }
    public static HearthboundClockSavedData load(CompoundTag tag) {
        if (!tag.contains("Tick", 4)) throw new IllegalStateException("Clock data missing Tick");
        return new HearthboundClockSavedData(tag.getLong("Tick"));
    }
    public static HearthboundClockSavedData get(MinecraftServer server) {
        return server.overworld().getDataStorage().computeIfAbsent(
            HearthboundClockSavedData::load, HearthboundClockSavedData::new, KEY);
    }
    public long advance() { long result=clock.advance(); setDirty(); return result; }
    public long tick() { return clock.current(); }
    @Override public CompoundTag save(CompoundTag tag) {
        tag.putLong("Tick", clock.current()); return tag;
    }
}