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
 * World-persistent, idempotent journal for sampled mill cycle evidence.
 * CANDIDATE is deliberately not a trusted Create process completion receipt.
 */
public final class MillEvidenceJournal extends SavedData {
    private static final String DATA_NAME = "hearthbound_mill_evidence_v1";
    private final Map<UUID, Entry> entries = new HashMap<>();

    public record Entry(UUID jobId, UUID citizenId, long machine, long processingTick,
                        long outputTick, int baselineFlour, int observedFlour) {
        public Entry {
            if (jobId == null || citizenId == null || processingTick <= 0
                    || outputTick <= processingTick || baselineFlour < 0
                    || observedFlour <= baselineFlour) {
                throw new IllegalArgumentException("Invalid candidate mill evidence");
            }
        }
    }

    private static MillEvidenceJournal get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(
            MillEvidenceJournal::load, MillEvidenceJournal::new, DATA_NAME);
    }

    public static MillEvidenceJournal load(CompoundTag root) {
        MillEvidenceJournal journal = new MillEvidenceJournal();
        ListTag list = root.getList("entries", Tag.TAG_COMPOUND);
        for (int i = 0; i < list.size(); i++) {
            CompoundTag t = list.getCompound(i);
            if (!t.hasUUID("jobId") || !t.hasUUID("citizenId")) {
                throw new IllegalStateException("Malformed mill evidence entry");
            }
            Entry entry = new Entry(
                t.getUUID("jobId"), t.getUUID("citizenId"), t.getLong("machine"),
                t.getLong("processingTick"), t.getLong("outputTick"),
                t.getInt("baselineFlour"), t.getInt("observedFlour"));
            if (journal.entries.putIfAbsent(entry.jobId(), entry) != null)
                throw new IllegalStateException("Duplicate job ID in mill evidence journal");
        }
        return journal;
    }

    @Override
    public CompoundTag save(CompoundTag root) {
        ListTag list = new ListTag();
        entries.values().stream().sorted((a, b) -> a.jobId().compareTo(b.jobId()))
            .forEach(e -> {
                CompoundTag t = new CompoundTag();
                t.putUUID("jobId", e.jobId());
                t.putUUID("citizenId", e.citizenId());
                t.putLong("machine", e.machine());
                t.putLong("processingTick", e.processingTick());
                t.putLong("outputTick", e.outputTick());
                t.putInt("baselineFlour", e.baselineFlour());
                t.putInt("observedFlour", e.observedFlour());
                list.add(t);
            });
        root.put("entries", list);
        return root;
    }

    /**
     * False means exact replay; conflicting replay is rejected. Never awards
     * learning credit. This is still subject to ordinary world-save durability.
     */
    public static boolean recordCandidate(ServerLevel level, Entry incoming) {
        MillEvidenceJournal journal = get(level);
        Entry existing = journal.entries.get(incoming.jobId());
        if (existing != null) {
            if (!existing.equals(incoming))
                throw new IllegalStateException("Conflicting mill evidence for job " + incoming.jobId());
            return false;
        }
        journal.entries.put(incoming.jobId(), incoming);
        journal.setDirty();
        return true;
    }

    public static String inspect(ServerLevel level, UUID jobId) {
        Entry entry = get(level).entries.get(jobId);
        if (entry == null) return "MILL_EVIDENCE NONE job=" + jobId + " NO_RESEARCH_CREDIT";
        return "MILL_EVIDENCE CANDIDATE job=" + jobId
            + " citizen=" + entry.citizenId()
            + " machine=" + BlockPos.of(entry.machine())
            + " processingTick=" + entry.processingTick()
            + " outputTick=" + entry.outputTick()
            + " baselineFlour=" + entry.baselineFlour()
            + " observedFlour=" + entry.observedFlour()
            + " NO_RESEARCH_CREDIT";
    }
}
