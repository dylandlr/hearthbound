package dev.hearthbound.integration;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.saveddata.SavedData;

/** Checkpointed diagnostic observations. Not atomic with machine saves; never grants credit. */
public final class MillingObservationSavedData extends SavedData {
    private static final String KEY = "hearthbound_milling_observations_v1";
    private static final int LIMIT = 10000;
    private final Map<UUID, CompoundTag> observations = new LinkedHashMap<>();

    public static MillingObservationSavedData get(MinecraftServer server) {
        return server.overworld().getDataStorage().computeIfAbsent(
                MillingObservationSavedData::load, MillingObservationSavedData::new, KEY);
    }

    public boolean append(CompoundTag observation) {
        validate(observation);
        UUID id = observation.getUUID("Id");
        CompoundTag existing = observations.get(id);
        if (existing != null) {
            if (!existing.equals(observation)) throw new IllegalArgumentException("Conflicting observation ID");
            return false;
        }
        if (observations.size() >= LIMIT) throw new IllegalStateException("Diagnostic journal capacity reached");
        observations.put(id, observation.copy());
        setDirty();
        return true;
    }

    public CompoundTag find(UUID id) {
        CompoundTag value = observations.get(id);
        return value == null ? null : value.copy();
    }

    public ListTag snapshot() {
        ListTag list = new ListTag();
        observations.values().forEach(value -> list.add(value.copy()));
        return list;
    }

    public static MillingObservationSavedData load(CompoundTag tag) {
        if (!tag.contains("Version", Tag.TAG_INT) || tag.getInt("Version") != 1
                || !tag.contains("Observations", Tag.TAG_LIST))
            throw new IllegalArgumentException("Invalid milling journal schema");
        MillingObservationSavedData result = new MillingObservationSavedData();
        ListTag list = tag.getList("Observations", Tag.TAG_COMPOUND);
        if (list.size() != ((ListTag) tag.get("Observations")).size())
            throw new IllegalArgumentException("Invalid observation list type");
        for (int i = 0; i < list.size(); i++) {
            if (!result.append(list.getCompound(i)))
                throw new IllegalArgumentException("Duplicate persisted observation");
        }
        result.setDirty(false);
        return result;
    }

    private static void validate(CompoundTag value) {
        if (!value.hasUUID("Id") || !value.hasUUID("Session")
                || !value.contains("Tick", Tag.TAG_LONG) || value.getLong("Tick") < 0
                || !value.contains("Position", Tag.TAG_LONG)
                || value.getString("Dimension").isBlank()
                || value.getString("Recipe").isBlank()
                || value.getString("Quality").isBlank()
                || !value.contains("InputBefore", Tag.TAG_COMPOUND)
                || !value.contains("InputAfter", Tag.TAG_COMPOUND)
                || !value.contains("OutputBefore", Tag.TAG_LIST)
                || !value.contains("OutputAfter", Tag.TAG_LIST))
            throw new IllegalArgumentException("Incomplete milling observation");
    }

    @Override public CompoundTag save(CompoundTag tag) {
        tag.putInt("Version", 1);
        tag.put("Observations", snapshot());
        return tag;
    }
}
