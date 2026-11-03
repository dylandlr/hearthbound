package dev.hearthbound.world;

import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Citizen-owned remembered source observations. Never consults world inventory
 * on read and never issues a task. Stored in persistent villager NBT, separately
 * from the session-local operator receipt ring.
 *
 * MEMORY IS NOT AN INVENTORY TRANSACTION REVISION OR EXECUTION AUTHORITY.
 */
public final class CitizenSourceKnowledge {
    public static final String SCHEMA = "hearthbound.citizen-source-knowledge.v1";
    private static final String ROOT = "hearthbound.source_knowledge.v1";
    private static final String ENTRIES = "entries";
    public static final int MAX_ENTRIES = 16;
    public static final long FRESH_TICKS = 40L;

    private CitizenSourceKnowledge() {}

    private static String key(ServerLevel level, BlockPos source) {
        return level.dimension().location().toString() + "|" +
            source.getX() + "," + source.getY() + "," + source.getZ();
    }

    /** Only call after SourceWheatObservation.inspect returned a known state. */
    public static void remember(ServerLevel level, BlockPos source, Villager observer,
                                SourceWheatObservation.Snapshot snapshot) {
        if (level == null || source == null || observer == null || snapshot == null)
            throw new IllegalArgumentException("missing knowledge evidence");
        if (snapshot.state() == SourceWheatObservation.State.UNKNOWN ||
                snapshot.tick() != level.getGameTime() ||
                !observer.level().dimension().equals(level.dimension()) ||
                !observer.getPersistentData().getBoolean("hearthbound.sable") ||
                !"OBSERVED".equals(snapshot.reason()) ||
                !level.hasChunkAt(source) ||
                observer.distanceToSqr(source.getX() + 0.5, source.getY() + 0.5,
                    source.getZ() + 0.5) > 16.0 * 16.0)
            throw new IllegalArgumentException("not a verified local citizen observation");
        CompoundTag root = observer.getPersistentData().getCompound(ROOT);
        ListTag entries = root.getList(ENTRIES, Tag.TAG_COMPOUND);
        ListTag updated = new ListTag();
        String identity = key(level, source);
        int revision = 1;
        for (int i = 0; i < entries.size(); i++) {
            CompoundTag old = entries.getCompound(i);
            if (identity.equals(old.getString("source"))) {
                // A personal knowledge revision is independent of receipt revisions.
                revision = old.getInt("revision") + 1;
            } else {
                updated.add(old.copy());
            }
        }
        // The oldest entry is evicted first, without inspecting remote sources.
        while (updated.size() >= MAX_ENTRIES) updated.remove(0);
        CompoundTag observation = new CompoundTag();
        observation.putString("source", identity);
        observation.putString("state", snapshot.state().name());
        observation.putInt("wheat", snapshot.wheat());
        observation.putLong("observed_tick", snapshot.tick());
        observation.putInt("revision", revision);
        observation.putString("origin", "DIRECT_FORGE_OBSERVATION");
        updated.add(observation);
        root.putString("schema", SCHEMA);
        root.put(ENTRIES, updated);
        observer.getPersistentData().put(ROOT, root);
    }

    /** Explicit citizen-scoped operator read. Does not resample or force chunks. */
    public static String inspect(ServerLevel level, BlockPos source, Villager citizen) {
        if (level == null || source == null || citizen == null)
            throw new IllegalArgumentException("missing knowledge query");
        String prefix = "CITIZEN_KNOWLEDGE schema=" + SCHEMA
            + " citizen=" + citizen.getUUID()
            + " source=" + key(level, source);
        if (!citizen.getPersistentData().getBoolean("hearthbound.sable"))
            return prefix + " status=DENIED reason=UNMARKED_CITIZEN action_authorized=false";
        ListTag entries = citizen.getPersistentData().getCompound(ROOT)
            .getList(ENTRIES, Tag.TAG_COMPOUND);
        for (int i = 0; i < entries.size(); i++) {
            CompoundTag entry = entries.getCompound(i);
            if (!key(level, source).equals(entry.getString("source"))) continue;
            long tick = entry.getLong("observed_tick");
            long age = level.getGameTime() - tick;
            // Negative age is conservatively stale (e.g. reset/replaced world clock).
            String freshness = age >= 0 && age <= FRESH_TICKS ? "FRESH" : "STALE";
            return prefix + " status=KNOWN freshness=" + freshness
                + " state=" + entry.getString("state")
                + " wheat=" + entry.getInt("wheat")
                + " observed_tick=" + tick
                + " age_ticks=" + age
                + " revision=" + entry.getInt("revision")
                + " origin=" + entry.getString("origin")
                + " action_authorized=false";
        }
        return prefix + " status=UNKNOWN action_authorized=false";
    }
}
