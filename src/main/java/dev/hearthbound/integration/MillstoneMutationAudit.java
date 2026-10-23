package dev.hearthbound.integration;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import com.simibubi.create.AllRecipeTypes;
import net.minecraftforge.items.wrapper.RecipeWrapper;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
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
    private static final UUID SERVER_SESSION_ID = UUID.randomUUID();
    private MillstoneMutationAudit() {}

    public record Snapshot(ItemStack input, List<ItemStack> outputs, String candidateRecipeId) {}

    public static Snapshot before(MillstoneBlockEntity millstone) {
        List<ItemStack> outputs = new ArrayList<>();
        for (int i = 0; i < millstone.outputInv.getSlots(); i++)
            outputs.add(millstone.outputInv.getStackInSlot(i).copy());
        String candidateRecipeId = "unresolved";
        if (millstone.getLevel() != null && !millstone.getLevel().isClientSide()) {
            candidateRecipeId = AllRecipeTypes.MILLING.find(new RecipeWrapper(millstone.inputInv), millstone.getLevel())
                    .map(recipe -> recipe.getId().toString()).orElse("unresolved");
        }
        return new Snapshot(millstone.inputInv.getStackInSlot(0).copy(), List.copyOf(outputs), candidateRecipeId);
    }

    public static void after(MillstoneBlockEntity millstone, Snapshot previous) {
        if (previous == null || millstone.getLevel() == null || millstone.getLevel().isClientSide()) return;
        ItemStack afterInput = millstone.inputInv.getStackInSlot(0);
        int consumed = ItemStack.isSameItemSameTags(previous.input(), afterInput)
                ? previous.input().getCount() - afterInput.getCount()
                : afterInput.isEmpty() ? previous.input().getCount() : -1;
        if (consumed != 1) return; // No verified single-item input consumption.
        List<String> deltas = new ArrayList<>();
        boolean ambiguousOutputs = false;
        for (int i = 0; i < millstone.outputInv.getSlots(); i++) {
            ItemStack old = previous.outputs().get(i);
            ItemStack now = millstone.outputInv.getStackInSlot(i);
            int increase = now.isEmpty() ? 0 : ItemStack.isSameItemSameTags(old, now)
                    ? now.getCount() - old.getCount()
                    : old.isEmpty() ? now.getCount() : -1;
            if (increase > 0) deltas.add(ForgeRegistries.ITEMS.getKey(now.getItem()) + "x" + increase);
            if (increase < 0) ambiguousOutputs = true;
        }
        String outputEvidence = ambiguousOutputs ? "ambiguous" : deltas.isEmpty() ? "none_observed" : "positive_deltas";
        UUID observationId = UUID.randomUUID();
        long logicalTick = ForgeServerTickObserver.logicalTick(millstone.getLevel().getServer());
        // UUIDs identify observations within this server session; they are not durable operation receipts.
        LOGGER.info("HEARTHBOUND_MILLSTONE_MUTATION session={} observation={} worldName={} dimension={} pos={} logicalTick={} input={} consumed=1 candidateRecipe={} outputs={} outputEvidence={} evidence=diagnostic_only researchCredit=false",
                SERVER_SESSION_ID, observationId, millstone.getLevel().getServer().getWorldData().getLevelName(),
                millstone.getLevel().dimension().location(), millstone.getBlockPos(), logicalTick,
                ForgeRegistries.ITEMS.getKey(previous.input().getItem()), previous.candidateRecipeId(), deltas, outputEvidence);
    }
}
