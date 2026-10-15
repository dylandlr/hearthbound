package dev.hearthbound.jobs;

import java.util.ArrayList;
import java.util.Comparator;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/** Approach inventories from supported, clear positions beside the station. */
public final class StationApproach {
    public static final double REACH_SQUARED = 4.0;

    private StationApproach() {}

    public static boolean inReach(Villager worker, BlockPos station) {
        BlockPos feet = worker.blockPosition();
        return Math.abs(feet.getX() - station.getX()) + Math.abs(feet.getZ() - station.getZ()) == 1
                && Math.abs(feet.getY() - station.getY()) <= 1
                && worker.distanceToSqr(station.getX() + .5, station.getY() + .5,
                        station.getZ() + .5) <= REACH_SQUARED;
    }

    public static boolean moveTo(ServerLevel level, Villager worker, BlockPos station) {
        var candidates = new ArrayList<BlockPos>();
        for (Direction side : Direction.Plane.HORIZONTAL) {
            for (int dy = -1; dy <= 1; dy++) {
                BlockPos feet = station.relative(side).above(dy);
                if (!standable(level, feet)) continue;
                candidates.add(feet);
            }
        }
        candidates.sort(Comparator.comparingDouble(feet -> worker.distanceToSqr(
                feet.getX() + .5, feet.getY(), feet.getZ() + .5)));
        for (BlockPos feet : candidates)
            if (moveToFeet(level, worker, feet, station)) return true;
        worker.getNavigation().stop();
        return false;
    }

    public static boolean standable(ServerLevel level, BlockPos feet) {
        return level.hasChunkAt(feet)
                && feet.getY() >= level.getMinBuildHeight() && feet.getY() + 1 < level.getMaxBuildHeight()
                && level.getFluidState(feet).isEmpty() && level.getFluidState(feet.above()).isEmpty()
                && level.getBlockState(feet).getCollisionShape(level, feet).isEmpty()
                && level.getBlockState(feet.above()).getCollisionShape(level, feet.above()).isEmpty()
                && level.getBlockState(feet.below()).isFaceSturdy(level, feet.below(), Direction.UP);
    }

    /** A complete route that avoids climbing onto any protected station. */
    public static boolean moveToFeet(ServerLevel level, Villager worker, BlockPos feet, BlockPos... stations) {
        if (!standable(level, feet)) return false;
        var path = worker.getNavigation().createPath(feet, 0);
        if (path == null || !path.canReach()) return false;
        // Skip the initial node so a worker already atop a station may step off.
        for (int i = 1; i < path.getNodeCount(); i++) {
            var node = path.getNode(i);
            for (BlockPos station : stations)
                if (node.x == station.getX() && node.z == station.getZ() && node.y >= station.getY())
                    return false;
        }
        return worker.getNavigation().moveTo(path, 1.0);
    }
}
