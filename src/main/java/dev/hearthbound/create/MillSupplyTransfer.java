package dev.hearthbound.create;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.items.IItemHandler;

/**
 * First Mill logistics adapter: atomically within one server tick, move wheat
 * from a vanilla storage barrel into a real Create millstone item handler.
 * This is infrastructure for citizen-driven deliveries, not a simulated recipe.
 * WARNING: not crash-atomic across a forced power loss.
 */
public final class MillSupplyTransfer {
    private MillSupplyTransfer() {}

    public static int transfer(CommandSourceStack command, BlockPos from, BlockPos millPos, int amount) {
        var level = command.getLevel();
        if (amount < 1 || amount > 64 || from.equals(millPos)
                || !level.hasChunkAt(from) || !level.hasChunkAt(millPos))
            return fail(command, "invalid_positions_or_amount");
        if (!(level.getBlockEntity(from) instanceof BarrelBlockEntity barrel))
            return fail(command, "source_not_barrel");
        BlockEntity mill = level.getBlockEntity(millPos);
        if (mill == null || !level.getBlockState(millPos).is(
                BuiltInRegistries.BLOCK.get(new ResourceLocation("create", "millstone"))))
            return fail(command, "destination_not_create_millstone");
        var optional = mill.getCapability(ForgeCapabilities.ITEM_HANDLER, Direction.UP);
        if (!optional.isPresent()) return fail(command, "no_create_input_handler");
        IItemHandler input = optional.orElseThrow(IllegalStateException::new);

        int available = 0;
        for (int i = 0; i < barrel.getContainerSize(); i++)
            if (barrel.getItem(i).is(Items.WHEAT)) available += barrel.getItem(i).getCount();
        if (available < amount) return fail(command, "insufficient_wheat");

        // Simulate all inserts before withdrawing any physical wheat.
        ItemStack remainder = new ItemStack(Items.WHEAT, amount);
        for (int i = 0; i < input.getSlots() && !remainder.isEmpty(); i++)
            remainder = input.insertItem(i, remainder, true);
        if (!remainder.isEmpty()) return fail(command, "mill_input_full");

        int removed = 0;
        for (int i = 0; i < barrel.getContainerSize() && removed < amount; i++) {
            ItemStack stack = barrel.getItem(i);
            if (!stack.is(Items.WHEAT)) continue;
            int taking = Math.min(stack.getCount(), amount - removed);
            barrel.removeItem(i, taking);
            removed += taking;
        }
        if (removed != amount) return fail(command, "withdrawal_mismatch");

        remainder = new ItemStack(Items.WHEAT, removed);
        for (int i = 0; i < input.getSlots() && !remainder.isEmpty(); i++)
            remainder = input.insertItem(i, remainder, false);
        if (!remainder.isEmpty()) {
            // Best-effort rollback into source; no async tick interleaving.
            int restore = remainder.getCount();
            for (int i = 0; i < barrel.getContainerSize() && restore > 0; i++) {
                ItemStack slot = barrel.getItem(i);
                if (slot.is(Items.WHEAT) && slot.getCount() < slot.getMaxStackSize()) {
                    int n = Math.min(restore, slot.getMaxStackSize() - slot.getCount());
                    slot.grow(n);
                    barrel.setItem(i, slot);
                    restore -= n;
                } else if (slot.isEmpty()) {
                    barrel.setItem(i, new ItemStack(Items.WHEAT, restore));
                    restore = 0;
                }
            }
            return fail(command, "insertion_failed_rolled_back=" + (restore == 0));
        }
        barrel.setChanged();
        command.sendSuccess(() -> Component.literal("HB_MILL_SUPPLY_PASS barrel_removed=" + amount
                + " mill_inserted=" + amount), false);
        return 1;
    }

    private static int fail(CommandSourceStack source, String reason) {
        source.sendFailure(Component.literal("HB_MILL_SUPPLY_FAIL " + reason));
        return 0;
    }
}
