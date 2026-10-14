package dev.hearthbound.create;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.items.IItemHandler;

/** First output collection probe using actual Create item capability. */
public final class FlourCollection {
    private FlourCollection() {}

    public static int collect(CommandSourceStack source, BlockPos millPos, BlockPos barrelPos, int limit) {
        var level = source.getLevel();
        if (limit < 1 || limit > 64 || millPos.equals(barrelPos)
                || !level.hasChunkAt(millPos) || !level.hasChunkAt(barrelPos))
            return fail(source, "invalid_request");
        if (!level.getBlockState(millPos).is(BuiltInRegistries.BLOCK.get(
                new ResourceLocation("create", "millstone"))))
            return fail(source, "not_millstone");
        var mill = level.getBlockEntity(millPos);
        if (mill == null || !(level.getBlockEntity(barrelPos) instanceof BarrelBlockEntity barrel))
            return fail(source, "missing_machine_or_barrel");
        // Horizontal face accesses the millstone's output, not its top input.
        var cap = mill.getCapability(ForgeCapabilities.ITEM_HANDLER, Direction.EAST);
        if (!cap.isPresent()) return fail(source, "output_handler_unavailable");
        IItemHandler output = cap.orElseThrow(IllegalStateException::new);
        var flour = BuiltInRegistries.ITEM.get(new ResourceLocation("create", "wheat_flour"));
        int remaining = limit;
        int moved = 0;
        for (int i = 0; i < output.getSlots() && remaining > 0; i++) {
            ItemStack available = output.getStackInSlot(i);
            if (!available.is(flour)) continue;
            ItemStack preview = output.extractItem(i, remaining, true);
            if (preview.isEmpty()) continue;
            int fits = 0;
            for (int slot = 0; slot < barrel.getContainerSize(); slot++) {
                ItemStack current = barrel.getItem(slot);
                if (current.isEmpty()) fits += Math.min(64, barrel.getMaxStackSize());
                else if (current.is(flour)) fits += Math.max(0, Math.min(current.getMaxStackSize(),
                        barrel.getMaxStackSize()) - current.getCount());
            }
            int toMove = Math.min(preview.getCount(), fits);
            if (toMove <= 0) break;
            ItemStack taken = output.extractItem(i, toMove, false);
            int toInsert = taken.getCount();
            for (int slot = 0; slot < barrel.getContainerSize() && toInsert > 0; slot++) {
                ItemStack existing = barrel.getItem(slot);
                if (existing.is(flour)) {
                    int n = Math.min(toInsert, Math.max(0, existing.getMaxStackSize() - existing.getCount()));
                    existing.grow(n);
                    barrel.setItem(slot, existing);
                    toInsert -= n;
                }
            }
            for (int slot = 0; slot < barrel.getContainerSize() && toInsert > 0; slot++) {
                if (!barrel.getItem(slot).isEmpty()) continue;
                int n = Math.min(toInsert, Math.min(64, barrel.getMaxStackSize()));
                barrel.setItem(slot, new ItemStack(flour, n));
                toInsert -= n;
            }
            if (toInsert != 0) return fail(source, "insertion_incomplete");
            moved += taken.getCount();
            remaining -= taken.getCount();
        }
        if (moved == 0) return fail(source, "no_extractable_flour_or_space");
        barrel.setChanged();
        final int count = moved;
        source.sendSuccess(() -> Component.literal("HB_FLOUR_COLLECTED count=" + count), false);
        return 1;
    }

    private static int fail(CommandSourceStack source, String reason) {
        source.sendFailure(Component.literal("HB_FLOUR_COLLECT_FAIL " + reason));
        return 0;
    }
}
