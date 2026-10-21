package dev.hearthbound.learning;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/** Pre-action observations persisted by real physical job ID; no inferred successor. */
public final class ResearchObservationSnapshotsSavedData extends SavedData {
    private static final String NAME = "hearthbound_research_observations_v1";
    private static final int LIMIT = 10000;
    public record Snapshot(UUID job, UUID citizen, long tick, double[] features) {
        public Snapshot {
            if (job == null || citizen == null || tick < 0 ||
                    features == null || features.length != ResearchObservationVector.WIDTH)
                throw new IllegalArgumentException("invalid pre-action snapshot");
            features = features.clone();
            for (double v : features)
                if (!Double.isFinite(v) || v < 0 || v > 1)
                    throw new IllegalArgumentException("invalid observation feature");
        }
        @Override public double[] features() { return features.clone(); }
        @Override public boolean equals(Object other) {
            return other instanceof Snapshot s && job.equals(s.job)
                    && citizen.equals(s.citizen) && tick == s.tick
                    && Arrays.equals(features,s.features);
        }
        @Override public int hashCode() { return job.hashCode() ^ citizen.hashCode()
                ^ Long.hashCode(tick) ^ Arrays.hashCode(features); }
    }

    private final Map<UUID,Snapshot> snapshots = new LinkedHashMap<>();
    private ResearchObservationSnapshotsSavedData() {}

    public static ResearchObservationSnapshotsSavedData get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(
                ResearchObservationSnapshotsSavedData::load,
                ResearchObservationSnapshotsSavedData::new, NAME);
    }
    public static ResearchObservationSnapshotsSavedData load(CompoundTag root) {
        var data = new ResearchObservationSnapshotsSavedData();
        var items = root.getList("snapshots",Tag.TAG_COMPOUND);
        if (items.size() > LIMIT) throw new IllegalStateException("too many observations");
        for (int i = 0; i < items.size(); i++) {
            var tag = items.getCompound(i);
            if (tag.getInt("schemaVersion") != ResearchObservationVector.VERSION)
                throw new IllegalArgumentException("unknown observation schema");
            var snapshot = new Snapshot(tag.getUUID("job"),tag.getUUID("citizen"),
                    tag.getLong("tick"),tag.getDoubleArray("features"));
            if (data.snapshots.putIfAbsent(snapshot.job(),snapshot) != null)
                throw new IllegalStateException("duplicate persisted observation job");
        }
        return data;
    }

    public synchronized void add(Snapshot snapshot) {
        if (snapshot == null) throw new IllegalArgumentException("null observation");
        var previous = snapshots.get(snapshot.job());
        if (previous != null) {
            if (!previous.equals(snapshot)) throw new IllegalStateException("conflicting observation");
            return;
        }
        if (snapshots.size() >= LIMIT) throw new IllegalStateException("observation capacity exceeded");
        snapshots.put(snapshot.job(),snapshot);
        setDirty();
    }
    public synchronized Snapshot require(UUID job) {
        var snapshot = snapshots.get(job);
        if (snapshot == null) throw new IllegalStateException("missing original observation");
        return snapshot;
    }
    public synchronized int size() { return snapshots.size(); }

    @Override public synchronized CompoundTag save(CompoundTag root) {
        ListTag list = new ListTag();
        for (var item : snapshots.values()) {
            CompoundTag tag = new CompoundTag();
            tag.putInt("schemaVersion",ResearchObservationVector.VERSION);
            tag.putUUID("job",item.job());
            tag.putUUID("citizen",item.citizen());
            tag.putLong("tick",item.tick());
            tag.putDoubleArray("features",item.features());
            list.add(tag);
        }
        root.put("snapshots",list);
        return root;
    }
}
