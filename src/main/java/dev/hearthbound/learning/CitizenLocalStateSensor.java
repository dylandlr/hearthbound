package dev.hearthbound.learning;

import dev.hearthbound.research.CitizenTechnologyKnowledge;
import dev.hearthbound.world.CitizenInstincts;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Citizen-owned attributes and locally accessible Minecraft status.
 * No recipe eligibility requirement and no chunk loading.
 */
public final class CitizenLocalStateSensor {
    public static final int VERSION = 1;
    public static final int WIDTH = 10;
    public record Snapshot(int version, double[] features) {
        public Snapshot {
            if (version != VERSION || features == null || features.length != WIDTH)
                throw new IllegalArgumentException("invalid citizen state");
            features = features.clone();
            for (double value : features) {
                if (!Double.isFinite(value) || value < 0 || value > 1)
                    throw new IllegalArgumentException("unnormalized citizen state");
            }
        }
        @Override public double[] features() { return features.clone(); }
    }

    private CitizenLocalStateSensor() {}

    /** null means citizen or local chunk not observable, not a terminal event. */
    public static Snapshot read(ServerLevel level, Villager citizen) {
        if (level == null || citizen == null || !citizen.isAlive()
                || citizen.level() != level || !level.hasChunkAt(citizen.blockPosition()))
            return null;
        var instincts = CitizenInstincts.get(citizen);
        var knowledge = CitizenTechnologyKnowledge.entries(citizen);
        boolean millingKnown = CitizenTechnologyKnowledge.knows(citizen, "create:milling/wheat");
        return new Snapshot(VERSION, new double[]{
                bounded(citizen.getHealth() / Math.max(1f,citizen.getMaxHealth())),
                bounded(instincts.getInt("food") / 100.0),
                bounded(instincts.getInt("shelter") / 100.0),
                bounded(instincts.getInt("danger") / 100.0),
                bounded(instincts.getInt("combat") / 100.0),
                bounded(instincts.getInt("exploration") / 100.0),
                bounded(instincts.getInt("cooperation") / 100.0),
                millingKnown ? 1 : 0,
                Math.min(1.0,knowledge.size() / 16.0),
                citizen.isBaby() ? 1 : 0
        });
    }

    private static double bounded(double n) { return Math.max(0,Math.min(1,n)); }
}
