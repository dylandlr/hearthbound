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
    private static final String RECIPE = "create:milling/wheat";
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
        if (!CitizenTechnologyKnowledge.knows(teacher, RECIPE)) return;

        // Inference is restricted to nearby Hearthbound citizens, not global knowledge.
        Villager student = level.getEntitiesOfClass(Villager.class,
                new AABB(teacher.blockPosition()).inflate(4.0),
                v -> v != teacher && v.getPersistentData().getBoolean("hearthbound.sable")
                     && teacher.hasLineOfSight(v))
                .stream().filter(v -> !CitizenTechnologyKnowledge.knows(v, RECIPE))
                .min(Comparator.comparingDouble(teacher::distanceToSqr))
                .orElse(null);
        if (student == null) return;

        double cooperation = CitizenInstincts.get(teacher).getInt("cooperation") / 100.0;
        double confidence = CitizenTechnologyKnowledge.require(teacher, RECIPE).confidence();
        // Reputation is a citizen-local observation, not a global social score.
        CompoundTag memory = tag.getCompound("hearthbound.socialV1");
        double familiarity = Math.min(1.0, Math.max(0.0,
                memory.getInt("reputation_" + student.getUUID()) / 100.0));
        // Urgency/fatigue currently neutral defaults until the physiological
        // and job-observation schemas provide authoritative inputs.
        var observation = new SocialTeachingPolicy.Observation(
                SocialTeachingPolicy.SCHEMA_VERSION, cooperation, confidence,
                familiarity, 0.5, 0.0, true, true, false);
        if (POLICY.select(observation).action() != SocialTeachingPolicy.Action.TEACH)
            return;
        CitizenTechnologyKnowledge.teach(teacher, student, RECIPE, now);
        org.apache.logging.log4j.LogManager.getLogger("HearthboundSocial")
                .info("HEARTHBOUND_AUTONOMOUS_TEACH teacher={} student={} recipe={}",
                        teacher.getUUID(), student.getUUID(), RECIPE);
    }
}
