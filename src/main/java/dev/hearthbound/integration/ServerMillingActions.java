package dev.hearthbound.integration;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

/** Server-authoritative primitive for a citizen's milling work order.
 * The caller must establish citizen assignment and resource ownership;
 * this primitive will not mint resources or activate machinery.
 */
public final class ServerMillingActions {
    private ServerMillingActions() {}

    /**
     * Extracts existing Create millstone output. Returns the extracted stack;
     * never constructs items that were not present in the output inventory.
     * Work-order authorization and credited results remain the caller's duty.
     */
    public static ItemStack collectOutput(MillstoneBlockEntity mill, int slot, int limit) {
        if (mill == null || mill.getLevel() == null || mill.getLevel().isClientSide()
                || mill.isRemoved() || limit <= 0 || slot < 0
                || slot >= mill.outputInv.getSlots()) return ItemStack.EMPTY;
        ItemStack present = mill.outputInv.getStackInSlot(slot);
        if (present.isEmpty()) return ItemStack.EMPTY;
        ItemStack extracted = mill.outputInv.extractItem(slot,
                Math.min(limit, present.getCount()), false);
        if (!extracted.isEmpty()) mill.setChanged();
        return extracted;
    }

    /** Transfers exactly one wheat from a supplied, server-owned stack. */
    public static boolean supplyWheat(MillstoneBlockEntity mill, ItemStack held) {
        if (mill == null || mill.getLevel() == null || mill.getLevel().isClientSide()
                || mill.isRemoved() || held == null || !held.is(Items.WHEAT)
                || held.getCount() < 1 || !mill.inputInv.getStackInSlot(0).isEmpty())
            return false;
        // Move the item; never duplicate the citizen's resource.
        ItemStack transferred = held.copy();
        transferred.setCount(1);
        mill.inputInv.setStackInSlot(0, transferred);
        held.shrink(1);
        mill.setChanged();
        return true;
    }
}
