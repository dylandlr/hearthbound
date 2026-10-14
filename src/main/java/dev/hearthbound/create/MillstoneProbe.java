package dev.hearthbound.create;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.nbt.CompoundTag;

/**
 * Read-only Create millstone instrumentation for integration testing.
 * Uses runtime block entity NBT without a compile-time dependency on Create.
 */
public final class MillstoneProbe {
    private MillstoneProbe() {}

    public static int inspect(CommandSourceStack source, BlockPos pos) {
        if (!source.getLevel().hasChunkAt(pos)) return failure(source, "chunk_unloaded");
        BlockEntity blockEntity = source.getLevel().getBlockEntity(pos);
        if (blockEntity == null || !source.getLevel().getBlockState(pos).getBlock()
                .equals(net.minecraft.core.registries.BuiltInRegistries.BLOCK
                    .get(new net.minecraft.resources.ResourceLocation("create", "millstone"))))
            return failure(source, "not_millstone");
        CompoundTag tag = blockEntity.saveWithFullMetadata();
        source.sendSuccess(() -> Component.literal("HB_MILL_NBT " + tag), false);
        return 1;
    }

    private static int failure(CommandSourceStack source, String reason) {
        source.sendFailure(Component.literal("HB_MILL_NBT_FAIL " + reason));
        return 0;
    }
}
