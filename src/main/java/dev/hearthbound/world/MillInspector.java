package dev.hearthbound.world;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.items.IItemHandler;
import net.minecraftforge.common.util.LazyOptional;

/**
 * Read-only Minecraft-side observation for the First Mill experiment.
 *
 * This intentionally avoids a hard Create dependency and never infers recipe
 * discovery from nearby stacks. Only a Create-specific processing completion
 * callback may produce learning evidence in a subsequent integration.
 */
public final class MillInspector {
    private static final ResourceLocation MILLSTONE =
        new ResourceLocation("create", "millstone");

    private MillInspector() {}

    public static String inspect(ServerLevel level, BlockPos pos) {
        if (!level.hasChunkAt(pos)) return "MILL UNLOADED pos=" + pos;
        ResourceLocation blockId = BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock());
        if (!MILLSTONE.equals(blockId))
            return "MILL NOT_CREATE_MILLSTONE pos=" + pos + " found=" + blockId;
        BlockEntity entity = level.getBlockEntity(pos);
        if (entity == null) return "MILL NO_BLOCK_ENTITY pos=" + pos;
        LazyOptional<IItemHandler> capability = entity.getCapability(ForgeCapabilities.ITEM_HANDLER);
        if (!capability.isPresent()) return "MILL NO_ITEM_HANDLER pos=" + pos;
        IItemHandler handler = capability.orElseThrow(IllegalStateException::new);
        int wheat = 0;
        int flour = 0;
        int occupied = 0;
        StringBuilder stacks = new StringBuilder();
        for (int i = 0; i < handler.getSlots(); i++) {
            ItemStack stack = handler.getStackInSlot(i);
            if (stack.isEmpty()) continue;
            occupied++;
            ResourceLocation item = BuiltInRegistries.ITEM.getKey(stack.getItem());
            if (item.equals(new ResourceLocation("minecraft", "wheat"))) wheat += stack.getCount();
            if (item.equals(new ResourceLocation("create", "wheat_flour"))) flour += stack.getCount();
            if (stacks.length() > 0) stacks.append(",");
            stacks.append(i).append(":").append(item).append("x").append(stack.getCount());
        }
        return "MILL OBSERVED pos=" + pos + " block=" + blockId
            + " slots=" + handler.getSlots() + " occupied=" + occupied
            + " wheat=" + wheat + " flour=" + flour + " stacks=[" + stacks + "]"
            + " PROCESS_UNVERIFIED NO_RESEARCH_CREDIT";
    }
}
