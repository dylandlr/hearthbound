package dev.hearthbound.research;

import dev.hearthbound.world.CitizenInstincts;
import dev.hearthbound.world.SableHauling;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.block.Blocks;

/** Bounded observation adapter. No global recipe scan and no chunk loads. */
public final class LocalMillExperimentSensor {
    private static final ExperimentSelectionPolicy POLICY = new ExperimentSelectionPolicy();
    private LocalMillExperimentSensor() {}

    public static ExperimentSelectionPolicy.Choice consider(
            ServerLevel level, Villager citizen, BlockPos source, BlockPos machine) {
        if (citizen.level() != level || !level.hasChunkAt(source) || !level.hasChunkAt(machine))
            return defer();
        if (citizen.blockPosition().distSqr(source) > 64
                || citizen.blockPosition().distSqr(machine) > 64)
            return defer();
        boolean wheat = SableHauling.hasAvailableWheat(level, source);
        boolean mill = level.getBlockState(machine).getBlock()
                .getDescriptionId().equals("block.create.millstone");
        // Only a recognized, loaded Create millstone is a possible experiment target.
        if (!wheat || !mill) return defer();
        String id = citizen.getUUID().toString();
        var data = TechnologyHypothesisSavedData.get(level);
        boolean previouslyFalsified = false;
        if (data.has(id,"create:milling/wheat")) {
            var h = data.require(id,"create:milling/wheat");
            if (h.status() != TechnologyHypotheses.Status.PROPOSED) return defer();
            return defer(); // Do not repeatedly propose an existing experiment.
        }
        double curiosity = CitizenInstincts.get(citizen).getInt("exploration")/100.0;
        var candidate = new ExperimentSelectionPolicy.Candidate(
                "create:milling/wheat","minecraft:wheat","create:millstone",
                "create:wheat_flour",0.8,0.2,true,true,previouslyFalsified);
        return POLICY.select(new ExperimentSelectionPolicy.Observation(
                ExperimentSelectionPolicy.VERSION,curiosity,0.5,0.0,List.of(candidate)));
    }
    private static ExperimentSelectionPolicy.Choice defer() {
        return new ExperimentSelectionPolicy.Choice(ExperimentSelectionPolicy.Action.DEFER,null,0);
    }
}
