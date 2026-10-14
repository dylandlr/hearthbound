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
        return tag;
    }

    public static boolean claim(ServerLevel level, BlockPos source, UUID citizenId) {
        HaulClaims data = get(level);
        UUID existing = data.claims.putIfAbsent(source.asLong(), citizenId);
        if (existing == null) data.setDirty();
        return existing == null || existing.equals(citizenId);
    }

    public static void release(ServerLevel level, BlockPos source, UUID citizenId) {
        HaulClaims data = get(level);
        if (data.claims.remove(source.asLong(), citizenId)) data.setDirty();
    }

    public static UUID owner(ServerLevel level, BlockPos source) {
        return get(level).claims.get(source.asLong());
    }
}
