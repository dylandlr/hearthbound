package dev.hearthbound.world;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/** Read-only candidate discovery; SableHauling.assign is still authoritative. */
public final class WheatSourceDiscovery {
    private static final int RADIUS = 8;
    private WheatSourceDiscovery() {}

    public static BlockPos nearest(ServerLevel level, Villager citizen, BlockPos destination) {
        BlockPos origin = citizen.blockPosition();
        BlockPos candidate = null;
        double closest = Double.POSITIVE_INFINITY;
        for (BlockPos pos : BlockPos.betweenClosed(
                origin.offset(-RADIUS, -2, -RADIUS),
                origin.offset(RADIUS, 2, RADIUS))) {
            if (pos.equals(destination) || !level.hasChunkAt(pos)) continue;
            if (!SableHauling.hasAvailableWheat(level, pos)) continue;
            if (HaulClaims.owner(level, pos) != null) continue;
            double distance = pos.distSqr(origin);
            if (distance < closest) {
                closest = distance;
                candidate = pos.immutable();
            }
        }
        return candidate;
    }
}
