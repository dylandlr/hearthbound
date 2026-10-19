package dev.hearthbound.research;

import dev.hearthbound.world.CitizenInstincts;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.AABB;

/**
 * Opt-in student initiative. Learners can react only to physically visible
 * nearby teachers advertising availability for a known recipe.
 */
public final class CitizenLearningInitiative {
    private static final String ENABLED = "hearthbound.autoLearnV1";
    private static final String LAST = "hearthbound.lastLearningConsiderationV1";
    private static final String RECIPE = "create:milling/wheat";
    private static final LearningRequestPolicy POLICY = new LearningRequestPolicy();
    private CitizenLearningInitiative() {}

    public static void setEnabled(Villager citizen, boolean enabled) {
        citizen.getPersistentData().putBoolean(ENABLED, enabled);
    }
    public static boolean enabled(Villager citizen) {
        return citizen.getPersistentData().getBoolean(ENABLED);
    }
    public static void tick(ServerLevel level, Villager student) {
        if (!enabled(student)) return;
        CompoundTag memory = student.getPersistentData();
        long now = level.getGameTime();
        if (now - memory.getLong(LAST) < 100) return;
        memory.putLong(LAST, now);
        if (CitizenTechnologyKnowledge.knows(student, RECIPE)) {
            CitizenLearningRequest.fulfilled(student, RECIPE);
            return;
        }
        // Teacher advertising is a public social signal visible within four blocks.
        // This is an explicit approximation until message perception is modeled.
        boolean teacherVisible = level.getEntitiesOfClass(Villager.class,
            new AABB(student.blockPosition()).inflate(4.0),
            v -> v != student && v.getPersistentData().getBoolean("hearthbound.sable")
                && CitizenSocialTeaching.enabled(v)
                && CitizenTechnologyKnowledge.knows(v, RECIPE)
                && student.hasLineOfSight(v)).size() > 0;
        double curiosity = CitizenInstincts.get(student).getInt("exploration") / 100.0;
        var observation = new LearningRequestPolicy.Observation(
            LearningRequestPolicy.VERSION, curiosity, 0, 0.6,
            false, teacherVisible, CitizenLearningRequest.requests(student, RECIPE));
        if (POLICY.select(observation) != LearningRequestPolicy.Action.REQUEST) return;
        CitizenLearningRequest.request(student, RECIPE);
        org.apache.logging.log4j.LogManager.getLogger("HearthboundSocial")
            .info("HEARTHBOUND_AUTONOMOUS_REQUEST student={} recipe={}",
                student.getUUID(), RECIPE);
    }
}
