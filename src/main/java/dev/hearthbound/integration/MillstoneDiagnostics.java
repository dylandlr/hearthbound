package dev.hearthbound.integration;

import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.registries.ForgeRegistries;

/**
 * Operator-only, read-only machine inspection.
 * Capability inventory is an instantaneous sample, NOT consumption evidence.
 */
public final class MillstoneDiagnostics {
    private MillstoneDiagnostics() {}

    public static int inspect(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
        CommandSourceStack source = ctx.getSource();
        ServerLevel level = source.getLevel();
        BlockPos pos = BlockPosArgument.getLoadedBlockPos(ctx, "pos");
        BlockEntity entity = level.getBlockEntity(pos);
        if (entity == null) {
            source.sendFailure(Component.literal("No block entity at " + pos.toShortString()));
            return 0;
        }
        ResourceLocation blockId = ForgeRegistries.BLOCKS.getKey(level.getBlockState(pos).getBlock());
        if (blockId == null || !"create".equals(blockId.getNamespace()) || !"millstone".equals(blockId.getPath())) {
            source.sendFailure(Component.literal("Target is not a Create millstone: " + blockId));
            return 0;
        }
        StringBuilder message = new StringBuilder()
            .append("dimension=").append(level.dimension().location())
            .append(" position=").append(pos.toShortString())
            .append(" hearthboundTick=").append(ForgeServerTickObserver.logicalTick(level.getServer()))
            .append(" blockEntity=").append(entity.getType())
            .append(" stacks=");
        final int[] count = {0};
        entity.getCapability(ForgeCapabilities.ITEM_HANDLER).ifPresent(handler -> {
            for (int slot = 0; slot < handler.getSlots(); slot++) {
                ItemStack stack = handler.getStackInSlot(slot);
                if (!stack.isEmpty()) {
                    if (count[0]++ > 0) message.append(",");
                    message.append(slot).append(":")
                        .append(ForgeRegistries.ITEMS.getKey(stack.getItem()))
                        .append("x").append(stack.getCount());
                }
            }
        });
        if (count[0] == 0) message.append("(none exposed)");
        source.sendSuccess(() -> Component.literal(message.toString()), false);
        return 1;
    }
}
