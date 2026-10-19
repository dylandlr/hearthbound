package dev.hearthbound.research;

import dev.hearthbound.world.SableHauling;
import java.util.Comparator;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Bounded, read-only physical survey: no global recipe registry, forced chunk
 * loading, inventory extraction or speculative technology unlock.
 */
public final class LocalExperimentDiscovery {
    public record Site(BlockPos wheatSource, BlockPos millstone) {}
    private LocalExperimentDiscovery() {}

    public static Site nearest(ServerLevel level, Villager citizen) {
        BlockPos origin = citizen.blockPosition();
        java.util.ArrayList<BlockPos> sources = new java.util.ArrayList<>();
        java.util.ArrayList<BlockPos> mills = new java.util.ArrayList<>();
        for (BlockPos next : BlockPos.betweenClosed(origin.offset(-8,-2,-8),
                                                    origin.offset(8,2,8))) {
            BlockPos pos = next.immutable();
            if (origin.distSqr(pos) > 64 || !level.hasChunkAt(pos)) continue;
            if (SableHauling.hasAvailableWheat(level,pos)) sources.add(pos);
            if ("create:millstone".equals(BuiltInRegistries.BLOCK
                    .getKey(level.getBlockState(pos).getBlock()).toString()))
                mills.add(pos);
        }
        Comparator<BlockPos> byDistance = Comparator.comparingDouble(
                (BlockPos p) -> origin.distSqr(p)).thenComparingLong(BlockPos::asLong);
        sources.sort(byDistance);
        mills.sort(byDistance);
        // Both positions must be locally observed. Ties are deterministic.
        if (sources.isEmpty() || mills.isEmpty()) return null;
        return new Site(sources.get(0),mills.get(0));
    }

    public static ExperimentSelectionPolicy.Choice consider(ServerLevel level,Villager citizen) {
        Site site=nearest(level,citizen);
        if(site==null) return new ExperimentSelectionPolicy.Choice(
                ExperimentSelectionPolicy.Action.DEFER,null,0);
        return LocalMillExperimentSensor.consider(level,citizen,site.wheatSource(),site.millstone());
    }
}
