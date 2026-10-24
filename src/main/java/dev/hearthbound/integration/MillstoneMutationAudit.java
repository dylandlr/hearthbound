package dev.hearthbound.integration;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import com.simibubi.create.content.kinetics.millstone.MillingRecipe;
import com.simibubi.create.AllRecipeTypes;
import net.minecraftforge.items.wrapper.RecipeWrapper;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import net.minecraft.world.item.ItemStack;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
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

    public static void after(MillstoneBlockEntity millstone, Snapshot previous, MillingRecipe executedRecipe) {
        if (previous == null || millstone.getLevel() == null || millstone.getLevel().isClientSide()) return;
        ItemStack afterInput = millstone.inputInv.getStackInSlot(0);
        int consumed = ItemStack.isSameItemSameTags(previous.input(), afterInput)
                ? previous.input().getCount() - afterInput.getCount()
                : afterInput.isEmpty() ? previous.input().getCount() : -1;
        if (consumed != 1) return; // No verified single-item input consumption.
        List<ItemStack> current = new ArrayList<>();
        for (int i = 0; i < millstone.outputInv.getSlots(); i++)
            current.add(millstone.outputInv.getStackInSlot(i).copy());
        var outputDelta = MinecraftInventoryDelta.compare(previous.outputs(), current);
        List<String> deltas = outputDelta.increased().stream()
                .map(stack -> stack.itemId() + "x" + stack.count()).toList();
        String outputEvidence = outputDelta.quality().name().toLowerCase(java.util.Locale.ROOT);
        String executedRecipeId = executedRecipe == null ? "unresolved" : executedRecipe.getId().toString();
        UUID observationId = UUID.randomUUID();
        long logicalTick = ForgeServerTickObserver.logicalTick(millstone.getLevel().getServer());
        CompoundTag record = new CompoundTag();
        record.putUUID("Id", observationId);
        record.putUUID("Session", SERVER_SESSION_ID);
        record.putLong("Tick", logicalTick);
        record.putString("Dimension", millstone.getLevel().dimension().location().toString());
        record.putLong("Position", millstone.getBlockPos().asLong());
        record.putString("Recipe", executedRecipeId);
        record.putString("CandidateRecipe", previous.candidateRecipeId());
        record.putString("Quality", outputEvidence);
        record.put("InputBefore", previous.input().save(new CompoundTag()));
        record.put("InputAfter", afterInput.save(new CompoundTag()));
        record.put("OutputBefore", serializeStacks(previous.outputs()));
        record.put("OutputAfter", serializeStacks(current));
        try {
            MillingObservationSavedData.get(millstone.getLevel().getServer()).append(record);
        } catch (RuntimeException failure) {
            // Observability must not abort Create's completed mutation or award credit.
            LOGGER.error("HEARTHBOUND_MILLING_JOURNAL_REJECTED observation=" + observationId, failure);
        }
        // SavedData checkpoints are not crash-atomic operation receipts.
        LOGGER.info("HEARTHBOUND_MILLSTONE_MUTATION session={} observation={} worldName={} dimension={} pos={} logicalTick={} input={} consumed=1 candidateRecipe={} executedRecipe={} recipeAgreement={} outputs={} outputEvidence={} evidence=diagnostic_only researchCredit=false",
                SERVER_SESSION_ID, observationId, millstone.getLevel().getServer().getWorldData().getLevelName(),
                millstone.getLevel().dimension().location(), millstone.getBlockPos(), logicalTick,
                ForgeRegistries.ITEMS.getKey(previous.input().getItem()), previous.candidateRecipeId(), executedRecipeId,
                previous.candidateRecipeId().equals(executedRecipeId), deltas, outputEvidence);
    }
    private static ListTag serializeStacks(List<ItemStack> stacks) {
        ListTag result = new ListTag();
        stacks.forEach(stack -> result.add(stack.save(new CompoundTag())));
        return result;
    }
}
