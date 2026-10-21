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

/**
 * Actual post-reward sampling status. UNAVAILABLE is not a fabricated successor.
 * Separate journal prevents silently filling zero-valued observations.
 */
public final class ResearchSuccessorObservationsSavedData extends SavedData {
    public enum Status { OBSERVED, UNAVAILABLE }
    public record Successor(UUID job, UUID citizen, long tick, Status status, double[] features) {
        public Successor {
            if (job == null || citizen == null || tick < 0 || status == null)
                throw new IllegalArgumentException("invalid successor identity");
            if (status == Status.OBSERVED) {
                if (features == null || features.length != ResearchObservationVector.WIDTH)
                    throw new IllegalArgumentException("missing successor features");
                features = features.clone();
                for (double value : features)
                    if (!Double.isFinite(value) || value < 0 || value > 1)
                        throw new IllegalArgumentException("invalid successor feature");
            } else if (features != null) {
                throw new IllegalArgumentException("unavailable successor must not have features");
            }
        }
        @Override public double[] features() { return features == null ? null : features.clone(); }
        @Override public boolean equals(Object other) {
            return other instanceof Successor s && job.equals(s.job) && citizen.equals(s.citizen)
                && tick == s.tick && status == s.status && Arrays.equals(features,s.features);
        }
        @Override public int hashCode() {
            return job.hashCode() ^ citizen.hashCode() ^ Long.hashCode(tick) ^
                status.hashCode() ^ Arrays.hashCode(features);
        }
    }

    private static final String NAME = "hearthbound_research_successors_v1";
    private static final int LIMIT = 10000;
    private final Map<UUID, Successor> values = new LinkedHashMap<>();
    private ResearchSuccessorObservationsSavedData() {}

    public static ResearchSuccessorObservationsSavedData get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(
            ResearchSuccessorObservationsSavedData::load,
            ResearchSuccessorObservationsSavedData::new, NAME);
    }
    public static ResearchSuccessorObservationsSavedData load(CompoundTag tag) {
        var result = new ResearchSuccessorObservationsSavedData();
        ListTag rows = tag.getList("successors", Tag.TAG_COMPOUND);
        if (rows.size() > LIMIT) throw new IllegalStateException("successor capacity exceeded");
        for (int i = 0; i < rows.size(); i++) {
            CompoundTag row = rows.getCompound(i);
            if (row.getInt("version") != 1) throw new IllegalArgumentException("unknown successor schema");
            Status status = Status.valueOf(row.getString("status"));
            var s = new Successor(row.getUUID("job"), row.getUUID("citizen"),
                row.getLong("tick"), status,
                status == Status.OBSERVED ? ObservationNbtCodec.get(row, "features") : null);
            if (result.values.putIfAbsent(s.job(),s) != null)
                throw new IllegalStateException("duplicate successor job");
        }
        return result;
    }
    public synchronized void record(Successor s) {
        if (s == null) throw new IllegalArgumentException("missing successor");
        Successor previous = values.get(s.job());
        if (previous != null) {
            if (!previous.equals(s)) throw new IllegalStateException("conflicting successor");
            return;
        }
        if (values.size() >= LIMIT) throw new IllegalStateException("successor capacity exceeded");
        values.put(s.job(),s);
        setDirty();
    }
    public synchronized Successor require(UUID job) {
        Successor s = values.get(job);
        if (s == null) throw new IllegalStateException("no successor sample");
        return s;
    }
    @Override public synchronized CompoundTag save(CompoundTag root) {
        ListTag rows = new ListTag();
        for (Successor s : values.values()) {
            CompoundTag row = new CompoundTag();
            row.putInt("version",1);
            row.putUUID("job",s.job()); row.putUUID("citizen",s.citizen());
            row.putLong("tick",s.tick()); row.putString("status",s.status().name());
            if (s.status() == Status.OBSERVED) ObservationNbtCodec.put(row, "features", s.features());
            rows.add(row);
        }
        root.put("successors",rows);
        return root;
    }
}
