package dev.hearthbound.research;

import dev.hearthbound.learning.OutcomeLedger;
import dev.hearthbound.world.MillProcessReceipts;
import dev.hearthbound.world.MillReservations;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.saveddata.SavedData;

/**
 * Persistent runtime reward journal for physically verified mill research.
 *
 * This is the Minecraft persistence layer for the same three-domain reward contract used by
 * OutcomeLedger. A job UUID can be rewarded only once.
 */
public final class MillResearchRewards extends SavedData {
    private static final String NAME = "hearthbound_mill_research_rewards_v1";
    private static final String WHEAT_MILLING = "create:milling/wheat";

    public record Award(
            UUID job,
            UUID citizen,
            long machine,
            long tick,
            OutcomeLedger.RewardVector reward,
            String evidenceId) {}

    private final Map<UUID, Award> awards = new HashMap<>();

    private MillResearchRewards() {}

    private static MillResearchRewards get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(
                MillResearchRewards::load,
                MillResearchRewards::new,
                NAME);
    }

    private static MillResearchRewards load(CompoundTag root) {
        MillResearchRewards data = new MillResearchRewards();
        ListTag list = root.getList("awards", Tag.TAG_COMPOUND);
        for (int i = 0; i < list.size(); i++) {
            CompoundTag tag = list.getCompound(i);
            Award award = new Award(
                    tag.getUUID("job"),
                    tag.getUUID("citizen"),
                    tag.getLong("machine"),
                    tag.getLong("tick"),
                    new OutcomeLedger.RewardVector(
                            tag.getDouble("personal"),
                            tag.getDouble("colony"),
                            tag.getDouble("research")),
                    tag.getString("evidence"));
            if (data.awards.putIfAbsent(award.job(), award) != null)
                throw new IllegalStateException("Duplicate research reward job");
        }
        return data;
    }

    @Override
    public CompoundTag save(CompoundTag root) {
        ListTag list = new ListTag();
        awards.values().stream()
                .sorted((a, b) -> a.job().compareTo(b.job()))
                .forEach(award -> {
                    CompoundTag tag = new CompoundTag();
                    tag.putUUID("job", award.job());
                    tag.putUUID("citizen", award.citizen());
                    tag.putLong("machine", award.machine());
                    tag.putLong("tick", award.tick());
                    tag.putDouble("personal", award.reward().personal());
                    tag.putDouble("colony", award.reward().colony());
                    tag.putDouble("research", award.reward().research());
                    tag.putString("evidence", award.evidenceId());
                    list.add(tag);
                });
        root.put("awards", list);
        return root;
    }

    public static Award awardVerified(
            ServerLevel level,
            Villager citizen,
            UUID job,
            BlockPos machine) {

        if (MillReservations.isTainted(level, job))
            throw new IllegalStateException("Tainted experiment cannot receive research reward");

        MillProcessReceipts.Receipt receipt =
                MillProcessReceipts.requireVerifiedReceipt(level, job, citizen.getUUID(), machine);

        MillResearchRewards journal = get(level);
        if (journal.awards.containsKey(job))
            throw new IllegalStateException("Research reward already granted for job " + job);

        int flourProduced = receipt.flourAfter() - receipt.flourBefore();
        double scale = Math.min(3.0, 1.0 + Math.log1p(Math.max(1, flourProduced)));
        OutcomeLedger.RewardVector reward = new OutcomeLedger.RewardVector(
                0.5 * scale,
                0.8 * scale,
                1.0 * scale);

        String evidenceId = "create:millstone:" + level.dimension().location()
                + ":" + machine.asLong() + ":" + job;

        Award award = new Award(
                job,
                citizen.getUUID(),
                machine.asLong(),
                level.getGameTime(),
                reward,
                evidenceId);

        CitizenTechnologyKnowledge.discover(
                citizen,
                WHEAT_MILLING,
                evidenceId,
                Math.min(1.0, 0.35 + reward.research() * 0.15),
                level.getGameTime());

        journal.awards.put(job, award);
        journal.setDirty();
        // Observability cannot interfere with server-authoritative research rewards.
        // Only a verified and durably journaled award is eligible for training attribution.
        try { ResearchTrainingRuntime.afterVerifiedAward(level, award); }
        catch (RuntimeException diagnosticFailure) {
            org.apache.logging.log4j.LogManager.getLogger("HearthboundLearning")
                    .warn("Optional training outcome attribution failed for job {}", job, diagnosticFailure);
        }
        return award;
    }

    public static boolean rewarded(ServerLevel level, UUID job) {
        return get(level).awards.containsKey(job);
    }

    public static String inspect(ServerLevel level, UUID job) {
        Award award = get(level).awards.get(job);
        if (award == null) return "RESEARCH_REWARD NONE job=" + job;
        return "RESEARCH_REWARD VERIFIED job=" + job
                + " citizen=" + award.citizen()
                + " personal=" + award.reward().personal()
                + " colony=" + award.reward().colony()
                + " research=" + award.reward().research()
                + " evidence=" + award.evidenceId();
    }
}
