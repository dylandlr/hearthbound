package dev.hearthbound.research;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

public final class LibraryCandidateDiscovery {
    private LibraryCandidateDiscovery() {}

    public static BlockPos nearest(ServerLevel level, Villager citizen) {
        BlockPos origin = citizen.blockPosition();
        BlockPos nearest = null;
        double best = Double.POSITIVE_INFINITY;
        for (BlockPos pos : BlockPos.betweenClosed(origin.offset(-8, -2, -8), origin.offset(8, 2, 8))) {
            if (!level.hasChunkAt(pos) || !LibraryStudyRuntime.hasBook(level, pos)) continue;
            double distance = pos.distSqr(origin);
            if (distance < best) {
                nearest = pos.immutable();
                best = distance;
            }
        }
        return nearest;
    }
}
