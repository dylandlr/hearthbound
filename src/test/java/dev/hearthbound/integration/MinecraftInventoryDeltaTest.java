package dev.hearthbound.integration;

import dev.hearthbound.research.InventoryDelta;
import java.util.List;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

/** In-process Minecraft ItemStack contract tests; uses built-in items only. */
public final class MinecraftInventoryDeltaTest {
    private static int checks;
    private static void ok(boolean v) { if (!v) throw new AssertionError("check " + (checks + 1)); checks++; }
    private static void quality(InventoryDelta.Quality q, ItemStack a, ItemStack b) {
        ok(MinecraftInventoryDelta.compare(List.of(a), List.of(b)).quality() == q);
    }
    public static void main(String[] args) {
        quality(InventoryDelta.Quality.NONE_OBSERVED, ItemStack.EMPTY, ItemStack.EMPTY);
        quality(InventoryDelta.Quality.POSITIVE_DELTAS, ItemStack.EMPTY, new ItemStack(Items.WHEAT, 1));
        quality(InventoryDelta.Quality.POSITIVE_DELTAS, new ItemStack(Items.WHEAT, 1), new ItemStack(Items.WHEAT, 3));
        quality(InventoryDelta.Quality.AMBIGUOUS, new ItemStack(Items.WHEAT, 3), new ItemStack(Items.WHEAT, 1));
        quality(InventoryDelta.Quality.AMBIGUOUS, new ItemStack(Items.WHEAT, 1), ItemStack.EMPTY);
        quality(InventoryDelta.Quality.AMBIGUOUS, new ItemStack(Items.WHEAT, 1), new ItemStack(Items.BREAD, 1));

        ItemStack tagged = new ItemStack(Items.WHEAT);
        CompoundTag tag = new CompoundTag();
        tag.putString("hearthbound_probe", "A");
        tagged.setTag(tag);
        quality(InventoryDelta.Quality.AMBIGUOUS, new ItemStack(Items.WHEAT), tagged);
        ItemStack sameTag = tagged.copy();
        sameTag.setCount(2);
        quality(InventoryDelta.Quality.POSITIVE_DELTAS, tagged, sameTag);

        ok(MinecraftInventoryDelta.compare(List.of(ItemStack.EMPTY), List.of(new ItemStack(Items.WHEAT, 4)))
                .increased().equals(List.of(new InventoryDelta.Stack("minecraft:wheat", 4))));
        try {
            MinecraftInventoryDelta.compare(List.of(ItemStack.EMPTY), List.of());
            throw new AssertionError("Expected slot count rejection");
        } catch (IllegalArgumentException expected) { checks++; }
        System.out.println("MinecraftInventoryDelta: " + checks + " checks passed");
    }
}
