package dev.hearthbound.learning;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/** Bounded persistent job-level unified observations; does not award or train. */
public final class UnifiedDecisionSnapshotsSavedData extends SavedData {
    private static final String NAME = "hearthbound_unified_decisions_v1";
    private static final int LIMIT = 10000;
    private final Map<UUID, UnifiedCitizenObservation.Snapshot> entries = new LinkedHashMap<>();
    private UnifiedDecisionSnapshotsSavedData() {}

    public static UnifiedDecisionSnapshotsSavedData get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(
                UnifiedDecisionSnapshotsSavedData::load,
                UnifiedDecisionSnapshotsSavedData::new, NAME);
    }

    public static UnifiedDecisionSnapshotsSavedData load(CompoundTag root) {
        var data = new UnifiedDecisionSnapshotsSavedData();
        ListTag rows = root.getList("observations", Tag.TAG_COMPOUND);
        if (rows.size() > LIMIT) throw new IllegalStateException("too many decision snapshots");
        for (int i = 0; i < rows.size(); i++) {
            CompoundTag t = rows.getCompound(i);
            var snapshot = new UnifiedCitizenObservation.Snapshot(
                    t.getInt("version"), t.getUUID("citizen"), t.getLong("tick"),
                    t.getInt("citizenSchema"), t.getDoubleArray("citizenFeatures"),
                    t.getInt("researchSchema"),
                    t.getBoolean("researchPresent") ? t.getDoubleArray("researchFeatures") : null);
            if (data.entries.putIfAbsent(t.getUUID("job"), snapshot) != null)
                throw new IllegalStateException("duplicate job snapshot");
        }
        return data;
    }

    public synchronized void record(UUID job, UnifiedCitizenObservation.Snapshot snapshot) {
        if (job == null || snapshot == null) throw new IllegalArgumentException("missing snapshot identity");
        var prior = entries.get(job);
        if (prior != null) {
            if (!same(prior, snapshot)) throw new IllegalStateException("conflicting job observation");
            return;
        }
        if (entries.size() >= LIMIT) throw new IllegalStateException("decision observation capacity reached");
        entries.put(job, snapshot);
        setDirty();
    }

    public synchronized UnifiedCitizenObservation.Snapshot require(UUID job) {
        var value = entries.get(job);
        if (value == null) throw new IllegalStateException("missing unified job observation");
        return value;
    }

    @Override public synchronized CompoundTag save(CompoundTag root) {
        ListTag rows = new ListTag();
        for (var entry : entries.entrySet()) {
            var s = entry.getValue();
            CompoundTag t = new CompoundTag();
            t.putUUID("job", entry.getKey());
            t.putInt("version",s.schemaVersion());
            t.putUUID("citizen",s.citizen());
            t.putLong("tick",s.gameTick());
            t.putInt("citizenSchema",s.citizenSchema());
            t.putDoubleArray("citizenFeatures",s.citizenFeatures());
            t.putInt("researchSchema",s.researchSchema());
            t.putBoolean("researchPresent",s.hasResearchContext());
            if (s.hasResearchContext()) t.putDoubleArray("researchFeatures",s.researchFeatures());
            rows.add(t);
        }
        root.put("observations",rows);
        return root;
    }

    private static boolean same(UnifiedCitizenObservation.Snapshot a, UnifiedCitizenObservation.Snapshot b) {
        return a.schemaVersion() == b.schemaVersion() && a.citizen().equals(b.citizen())
                && a.gameTick() == b.gameTick() && a.citizenSchema() == b.citizenSchema()
                && a.researchSchema() == b.researchSchema()
                && java.util.Arrays.equals(a.citizenFeatures(), b.citizenFeatures())
                && java.util.Arrays.equals(a.researchFeatures(), b.researchFeatures());
    }
}
