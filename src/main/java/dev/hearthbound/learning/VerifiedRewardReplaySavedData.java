package dev.hearthbound.learning;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/**
 * Durable replay of VERIFIED reward records. Not yet (s,a,r,s') transitions.
 * Does not infer missing attributions after server restart.
 */
public final class VerifiedRewardReplaySavedData extends SavedData {
    private static final String NAME = "hearthbound_verified_reward_replay_v1";
    private static final int MAX_RECORDS = 10000;
    private final LinkedHashMap<UUID, VerifiedTrainingTransitions.Transition> records = new LinkedHashMap<>();

    private VerifiedRewardReplaySavedData() {}

    public static VerifiedRewardReplaySavedData get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(
                VerifiedRewardReplaySavedData::load,
                VerifiedRewardReplaySavedData::new, NAME);
    }

    public static VerifiedRewardReplaySavedData load(CompoundTag root) {
        VerifiedRewardReplaySavedData result = new VerifiedRewardReplaySavedData();
        ListTag list = root.getList("records", Tag.TAG_COMPOUND);
        if (list.size() > MAX_RECORDS) throw new IllegalStateException("oversized replay data");
        for (int i = 0; i < list.size(); ++i) {
            CompoundTag tag = list.getCompound(i);
            UUID job = tag.getUUID("job");
            var reward = new OutcomeLedger.RewardVector(
                    tag.getDouble("personal"), tag.getDouble("colony"), tag.getDouble("research"));
            var record = new VerifiedTrainingTransitions.Transition(
                    tag.getInt("schemaVersion"), job, tag.getUUID("citizen"),
                    tag.getLong("decisionTick"), tag.getLong("outcomeTick"),
                    tag.getString("action"), tag.getString("recipeId"),
                    tag.getString("evidenceId"), reward);
            validate(record);
            if (result.records.putIfAbsent(job, record) != null)
                throw new IllegalStateException("duplicate job in replay data");
        }
        return result;
    }

    public synchronized boolean append(VerifiedTrainingTransitions.Transition record) {
        validate(record);
        var existing = records.get(record.job());
        if (existing != null) {
            if (!existing.equals(record)) throw new IllegalStateException("conflicting replay job");
            return false;
        }
        for (var previous : records.values()) {
            if (previous.evidenceId().equals(record.evidenceId()))
                throw new IllegalStateException("replayed evidence ID");
        }
        if (records.size() == MAX_RECORDS)
            records.remove(records.keySet().iterator().next());
        records.put(record.job(), record);
        setDirty();
        return true;
    }

    public synchronized Map<UUID, VerifiedTrainingTransitions.Transition> snapshot() {
        return Map.copyOf(records);
    }

    @Override
    public synchronized CompoundTag save(CompoundTag root) {
        ListTag list = new ListTag();
        for (var record : records.values()) {
            CompoundTag tag = new CompoundTag();
            tag.putInt("schemaVersion", record.schemaVersion());
            tag.putUUID("job", record.job());
            tag.putUUID("citizen", record.citizen());
            tag.putLong("decisionTick", record.decisionTick());
            tag.putLong("outcomeTick", record.outcomeTick());
            tag.putString("action", record.action());
            tag.putString("recipeId", record.recipeId());
            tag.putString("evidenceId", record.evidenceId());
            tag.putDouble("personal", record.reward().personal());
            tag.putDouble("colony", record.reward().colony());
            tag.putDouble("research", record.reward().research());
            list.add(tag);
        }
        root.put("records", list);
        return root;
    }

    private static void validate(VerifiedTrainingTransitions.Transition record) {
        if (record == null || record.schemaVersion() != 1
                || record.job() == null || record.citizen() == null || record.reward() == null
                || record.decisionTick() < 0 || record.outcomeTick() < record.decisionTick()
                || !"PROPOSE".equals(record.action())
                || record.recipeId() == null || record.recipeId().isBlank()
                || record.evidenceId() == null || record.evidenceId().isBlank())
            throw new IllegalArgumentException("invalid verified reward record");
    }
}
