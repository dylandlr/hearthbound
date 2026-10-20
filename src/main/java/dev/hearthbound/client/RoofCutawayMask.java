package dev.hearthbound.client;

import java.util.ArrayList;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Bounded terrain cutaway candidate calculation. Read-only: never mutates
 * the level, forces chunk loads, or exposes arbitrary unloaded geometry.
 *
 * The resulting mask is an input to the future section-aware chunk renderer.
 * It does not itself hide roof blocks.
 */
public final class RoofCutawayMask {
    private RoofCutawayMask() {}

    public static List<BlockPos> sample(Level level, BlockPos focus, int viewFloorY,
                                         int horizontalRadius, int verticalLimit) {
        int radius = Math.max(0, Math.min(8, horizontalRadius));
        int ceiling = Math.min(level.getMaxBuildHeight() - 1,
                Math.min(viewFloorY + 1, focus.getY() + Math.max(0, Math.min(24, verticalLimit))));
        int start = Math.max(level.getMinBuildHeight(), focus.getY() + 2);
        if (start > ceiling) return List.of();
        List<BlockPos> candidates = new ArrayList<>();
        for (int x = focus.getX() - radius; x <= focus.getX() + radius; x++) {
            for (int z = focus.getZ() - radius; z <= focus.getZ() + radius; z++) {
                for (int y = start; y <= ceiling; y++) {
                    BlockPos pos = new BlockPos(x, y, z);
                    if (!level.hasChunkAt(pos)) continue;
                    BlockState state = level.getBlockState(pos);
                    if (state.canOcclude() && state.isSolidRender(level, pos))
                        candidates.add(pos);
                }
            }
        }
        return List.copyOf(candidates);
    }
}
