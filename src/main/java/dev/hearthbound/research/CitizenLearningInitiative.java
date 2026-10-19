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
        // Read only explicit offers made by physically visible, opt-in citizens.
        java.util.List<Villager> visibleTeachers = level.getEntitiesOfClass(Villager.class,
                new AABB(student.blockPosition()).inflate(4.0),
                v -> v != student && v.getPersistentData().getBoolean("hearthbound.sable")
                        && student.hasLineOfSight(v));
        java.util.Set<String> offered = new java.util.TreeSet<>();
        for (Villager teacher : visibleTeachers)
            offered.addAll(TechnologyOffers.advertisedBy(teacher));
        String recipe = offered.stream()
                .filter(id -> !CitizenTechnologyKnowledge.knows(student, id))
                .findFirst().orElse(null);
        if (recipe == null) return;
        boolean teacherVisible = true;
        double curiosity = CitizenInstincts.get(student).getInt("exploration") / 100.0;
        var observation = new LearningRequestPolicy.Observation(
            LearningRequestPolicy.VERSION, curiosity, 0, 0.6,
            false, teacherVisible, CitizenLearningRequest.requests(student, recipe));
        if (POLICY.select(observation) != LearningRequestPolicy.Action.REQUEST) return;
        CitizenLearningRequest.request(student, recipe);
        org.apache.logging.log4j.LogManager.getLogger("HearthboundSocial")
            .info("HEARTHBOUND_AUTONOMOUS_REQUEST student={} recipe={}",
                student.getUUID(), recipe);
    }
}
