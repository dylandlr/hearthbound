package dev.hearthbound.world;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/**
 * Persistent, per-dimension source claims stored with the Minecraft world.
 *
 * A claim is not proof of a physical item transaction. Claims intentionally
 * survive restart and citizen removal until explicit release or admin repair.
 */
public final class HaulClaims extends SavedData {
    private static final String DATA_NAME = "hearthbound_haul_claims";
    private final Map<Long, UUID> claims = new HashMap<>();
    private final java.util.ArrayList<String> transitions = new java.util.ArrayList<>();
    private static final int HISTORY_LIMIT = 256;

    private void record(ServerLevel level, String action, BlockPos source, UUID owner) {
        transitions.add("tick=" + level.getGameTime() + " action=" + action
            + " source=" + source.toShortString() + " owner=" + owner);
        if (transitions.size() > HISTORY_LIMIT) transitions.remove(0);
        setDirty();
    }

    public static String history(ServerLevel level, BlockPos source) {
        String key = "source=" + source.toShortString() + " ";
        java.util.List<String> events = get(level).transitions.stream()
            .filter(entry -> entry.contains(key)).toList();
        return "CLAIM_HISTORY " + source.toShortString() + " events=" + events.size()
            + " | " + String.join(" | ", events);
    }

    public static HaulClaims get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(
            HaulClaims::load, HaulClaims::new, DATA_NAME);
    }

    public static HaulClaims load(CompoundTag tag) {
        HaulClaims data = new HaulClaims();
        ListTag entries = tag.getList("claims", Tag.TAG_COMPOUND);
        for (int i = 0; i < entries.size(); i++) {
            CompoundTag entry = entries.getCompound(i);
            if (entry.hasUUID("owner")) {
                data.claims.put(entry.getLong("source"), entry.getUUID("owner"));
            }
        }
        ListTag events = tag.getList("transitions", Tag.TAG_STRING);
        for (int i = 0; i < events.size(); i++) data.transitions.add(events.getString(i));
        return data;
    }

    @Override
    public CompoundTag save(CompoundTag tag) {
        ListTag entries = new ListTag();
        claims.forEach((source, owner) -> {
            CompoundTag item = new CompoundTag();
            item.putLong("source", source);
            item.putUUID("owner", owner);
            entries.add(item);
        });
        tag.put("claims", entries);
        ListTag events = new ListTag();
        for (String event : transitions) events.add(net.minecraft.nbt.StringTag.valueOf(event));
        tag.put("transitions", events);
        return tag;
    }

    public static boolean claim(ServerLevel level, BlockPos source, UUID citizenId) {
        HaulClaims data = get(level);
        UUID existing = data.claims.putIfAbsent(source.asLong(), citizenId);
        if (existing == null) data.record(level, "ACQUIRE", source, citizenId);
        return existing == null || existing.equals(citizenId);
    }

    public static void release(ServerLevel level, BlockPos source, UUID citizenId) {
        HaulClaims data = get(level);
        if (data.claims.remove(source.asLong(), citizenId)) data.record(level, "RELEASE", source, citizenId);
    }

    /**
     * Operator-initiated repair with optimistic owner matching.
     * Never removes a claim if its owner has changed since inspection.
     * Caller MUST separately verify physical cargo and inventories.
     */
    public static boolean releaseIfOwned(ServerLevel level, BlockPos source, UUID expectedOwner) {
        HaulClaims data = get(level);
        boolean removed = data.claims.remove(source.asLong(), expectedOwner);
        if (removed) data.record(level, "ADMIN_RELEASE", source, expectedOwner);
        return removed;
    }

    public static int count(ServerLevel level) {
        return get(level).claims.size();
    }

    public static UUID owner(ServerLevel level, BlockPos source) {
        return get(level).claims.get(source.asLong());
    }
}
