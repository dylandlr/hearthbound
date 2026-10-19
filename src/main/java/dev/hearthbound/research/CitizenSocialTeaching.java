package dev.hearthbound.research;

import dev.hearthbound.world.CitizenInstincts;
import java.util.Comparator;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.AABB;

/**
 * Opt-in, server-side social action executor. No global technology query.
 * The student's proximity and line of sight must be physically witnessed.
 */
public final class CitizenSocialTeaching {
    private static final String ENABLED = "hearthbound.autoTeachingV1";
    private static final String LAST_ATTEMPT = "hearthbound.lastTeachingAttemptV1";
    private static final SocialTeachingPolicy POLICY = new SocialTeachingPolicy();

    private CitizenSocialTeaching() {}

    public static void setEnabled(Villager citizen, boolean enabled) {
        citizen.getPersistentData().putBoolean(ENABLED, enabled);
    }

    public static boolean enabled(Villager citizen) {
        return citizen.getPersistentData().getBoolean(ENABLED);
    }

    public static void tick(ServerLevel level, Villager teacher) {
        if (!enabled(teacher)) return;
        long now = level.getGameTime();
        CompoundTag tag = teacher.getPersistentData();
        if (now - tag.getLong(LAST_ATTEMPT) < 100) return;
        tag.putLong(LAST_ATTEMPT, now);
        // Only personally held, explicitly advertised recipes are eligible.
        java.util.List<String> offered = TechnologyOffers.advertisedBy(teacher);
        if (offered.isEmpty()) return;
        java.util.List<Villager> visible = level.getEntitiesOfClass(Villager.class,
                new AABB(teacher.blockPosition()).inflate(4.0),
                v -> v != teacher && v.getPersistentData().getBoolean("hearthbound.sable")
                        && teacher.hasLineOfSight(v));
        record Candidate(Villager student, String recipe, boolean requested) {}
        java.util.List<Candidate> candidates = new java.util.ArrayList<>();
        for (Villager student : visible) {
            for (String recipe : offered) {
                if (!CitizenTechnologyKnowledge.knows(student, recipe))
                    candidates.add(new Candidate(student, recipe,
                            CitizenLearningRequest.requests(student, recipe)));
            }
        }
        Candidate selected = candidates.stream()
                .min(Comparator.comparingInt((Candidate v) -> v.requested() ? 0 : 1)
                        .thenComparingDouble(v -> teacher.distanceToSqr(v.student()))
                        .thenComparing(Candidate::recipe))
                .orElse(null);
        if (selected == null) return;
        Villager student = selected.student();
        String recipe = selected.recipe();

        double cooperation = CitizenInstincts.get(teacher).getInt("cooperation") / 100.0;
        double confidence = CitizenTechnologyKnowledge.require(teacher, recipe).confidence();
        // Reputation is a citizen-local observation, not a global social score.
        CompoundTag memory = tag.getCompound("hearthbound.socialV1");
        double familiarity = Math.min(1.0, Math.max(0.0,
                memory.getInt("reputation_" + student.getUUID()) / 100.0));
        // The request is observable only because the student is in range and visible.
        boolean requested = selected.requested();
        // Do not invent villager fatigue. It remains a neutral placeholder until
        // a physical needs model provides a measured signal.
        double urgency = requested ? 0.8 : 0.5;
        var observation = new SocialTeachingPolicy.Observation(
                SocialTeachingPolicy.SCHEMA_VERSION, cooperation, confidence,
                familiarity, urgency, 0.0, true, true, requested);
        if (POLICY.select(observation).action() != SocialTeachingPolicy.Action.TEACH)
            return;
        CitizenTechnologyKnowledge.teach(teacher, student, recipe, now);
        CitizenLearningRequest.fulfilled(student, recipe);
        org.apache.logging.log4j.LogManager.getLogger("HearthboundSocial")
                .info("HEARTHBOUND_AUTONOMOUS_TEACH teacher={} student={} recipe={}",
                        teacher.getUUID(), student.getUUID(), recipe);
    }
}
