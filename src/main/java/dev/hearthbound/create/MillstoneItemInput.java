package dev.hearthbound.create;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.items.IItemHandler;

/** Exercise actual Create item automation capability, not NBT injection. */
public final class MillstoneItemInput {
    private MillstoneItemInput() {}

    public static int feed(CommandSourceStack source, BlockPos pos, int requested) {
        if (requested < 1 || requested > 64 || !source.getLevel().hasChunkAt(pos))
            return fail(source, "bad_amount_or_chunk");
        BlockEntity machine = source.getLevel().getBlockEntity(pos);
        if (machine == null || !source.getLevel().getBlockState(pos).is(
                net.minecraft.core.registries.BuiltInRegistries.BLOCK.get(
                    new net.minecraft.resources.ResourceLocation("create", "millstone"))))
            return fail(source, "not_millstone");
        var capability = machine.getCapability(ForgeCapabilities.ITEM_HANDLER, net.minecraft.core.Direction.UP);
        if (!capability.isPresent()) return fail(source, "no_upward_item_handler");
        IItemHandler handler = capability.orElseThrow(IllegalStateException::new);
        int remaining = requested;
        for (int slot = 0; slot < handler.getSlots() && remaining > 0; slot++) {
            ItemStack result = handler.insertItem(slot, new ItemStack(Items.WHEAT, remaining), false);
            remaining = result.getCount();
        }
        int inserted = requested - remaining;
        if (inserted != requested) return fail(source, "partial_insert_" + inserted);
        source.sendSuccess(() -> Component.literal("HB_CREATE_WHEAT_INSERTED amount=" + inserted), false);
        return 1;
    }

    private static int fail(CommandSourceStack source, String reason) {
        source.sendFailure(Component.literal("HB_CREATE_INPUT_FAIL " + reason));
        return 0;
    }
}
