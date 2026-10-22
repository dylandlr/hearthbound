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
        // The active floor is the room being inspected, not a ceiling
        // cutoff. A roof two or three blocks above that floor must remain
        // eligible when the player presses End to follow its occupant.
        int limit = Math.max(0, Math.min(24, verticalLimit));
        int ceiling = Math.min(level.getMaxBuildHeight() - 1, focus.getY() + limit);
        int start = Math.max(level.getMinBuildHeight(),
                Math.max(focus.getY() + 2, viewFloorY + 1));
        if (start > ceiling) return List.of();
        List<BlockPos> candidates = new ArrayList<>();
        for (int x = focus.getX() - radius; x <= focus.getX() + radius; x++) {
            for (int z = focus.getZ() - radius; z <= focus.getZ() + radius; z++) {
                for (int y = start; y <= ceiling; y++) {
                    BlockPos pos = new BlockPos(x, y, z);
                    if (!level.hasChunkAt(pos)) continue;
                    BlockState state = level.getBlockState(pos);
                    // Only surfaces above accessible air are roof candidates.
                    // Ordinary solid cave mass must not be indiscriminately
                    // cut away; we will expand this to connected room volumes.
                    BlockPos below = pos.below();
                    if (state.canOcclude() && state.isSolidRender(level, pos)
                            && level.hasChunkAt(below)
                            && level.getBlockState(below).isAir())
                        candidates.add(pos);
                }
            }
        }
        return List.copyOf(candidates);
    }
}
