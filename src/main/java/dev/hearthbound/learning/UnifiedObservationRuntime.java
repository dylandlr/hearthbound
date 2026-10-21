package dev.hearthbound.learning;

import dev.hearthbound.research.ExperimentSelectionPolicy;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/** One decision-boundary snapshot, with citizen state and optional local research input. */
public final class UnifiedObservationRuntime {
    private UnifiedObservationRuntime() {}

    public static UnifiedCitizenObservation.Snapshot sample(
            ServerLevel level, Villager citizen, ExperimentSelectionPolicy.Observation research) {
        long tick = level.getGameTime();
        var local = CitizenLocalStateSensor.read(level, citizen);
        if (local == null) return null;
        var context = research == null ? null : ResearchObservationVector.from(research);
        return UnifiedCitizenObservation.combine(citizen.getUUID(), tick, local, context);
    }
}
