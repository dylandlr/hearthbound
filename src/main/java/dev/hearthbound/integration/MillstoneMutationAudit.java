package dev.hearthbound.integration;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.registries.ForgeRegistries;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * Called synchronously around Create's private millstone process() method.
 * Diagnostic only; never awards research credit.
 */
public final class MillstoneMutationAudit {
    private static final Logger LOGGER = LogManager.getLogger();
    private MillstoneMutationAudit() {}

    public record Snapshot(ItemStack input, List<ItemStack> outputs) {}

    public static Snapshot before(MillstoneBlockEntity millstone) {
        List<ItemStack> outputs = new ArrayList<>();
        for (int i = 0; i < millstone.outputInv.getSlots(); i++)
            outputs.add(millstone.outputInv.getStackInSlot(i).copy());
        return new Snapshot(millstone.inputInv.getStackInSlot(0).copy(), List.copyOf(outputs));
    }

    public static void after(MillstoneBlockEntity millstone, Snapshot previous) {
        if (previous == null || millstone.getLevel() == null || millstone.getLevel().isClientSide()) return;
        ItemStack afterInput = millstone.inputInv.getStackInSlot(0);
        int consumed = ItemStack.isSameItemSameTags(previous.input(), afterInput)
                ? previous.input().getCount() - afterInput.getCount()
                : afterInput.isEmpty() ? previous.input().getCount() : -1;
        if (consumed != 1) return; // No verified single-item input consumption.
        List<String> deltas = new ArrayList<>();
        for (int i = 0; i < millstone.outputInv.getSlots(); i++) {
            ItemStack old = previous.outputs().get(i);
            ItemStack now = millstone.outputInv.getStackInSlot(i);
            int increase = now.isEmpty() ? 0 : ItemStack.isSameItemSameTags(old, now)
                    ? now.getCount() - old.getCount()
                    : old.isEmpty() ? now.getCount() : -1;
            if (increase > 0) deltas.add(ForgeRegistries.ITEMS.getKey(now.getItem()) + "x" + increase);
        }
        LOGGER.info("HEARTHBOUND_MILLSTONE_MUTATION dimension={} pos={} input={} outputs={} proof=diagnostic_only",
                millstone.getLevel().dimension().location(), millstone.getBlockPos(),
                ForgeRegistries.ITEMS.getKey(previous.input().getItem()), deltas);
    }
}
