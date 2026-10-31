package dev.hearthbound.integration;

import dev.hearthbound.research.InventoryDelta;
import java.util.List;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

/** In-game diagnostic assertions; only run after Minecraft and Forge are initialized. */
public final class RuntimeInventoryDeltaChecks {
    private RuntimeInventoryDeltaChecks() {}

    public static int verify() {
        int passed = 0;
        passed += expect(InventoryDelta.Quality.NONE_OBSERVED, ItemStack.EMPTY, ItemStack.EMPTY);
        passed += expect(InventoryDelta.Quality.POSITIVE_DELTAS, ItemStack.EMPTY, new ItemStack(Items.WHEAT, 1));
        passed += expect(InventoryDelta.Quality.POSITIVE_DELTAS,
                new ItemStack(Items.WHEAT, 1), new ItemStack(Items.WHEAT, 3));
        passed += expect(InventoryDelta.Quality.AMBIGUOUS,
                new ItemStack(Items.WHEAT, 3), new ItemStack(Items.WHEAT, 1));
        passed += expect(InventoryDelta.Quality.AMBIGUOUS,
                new ItemStack(Items.WHEAT), new ItemStack(Items.BREAD));
        passed += expect(InventoryDelta.Quality.AMBIGUOUS, new ItemStack(Items.WHEAT), ItemStack.EMPTY);
        ItemStack tagged = new ItemStack(Items.WHEAT);
        CompoundTag tag = new CompoundTag();
        tag.putString("hearthbound_probe", "A");
        tagged.setTag(tag);
        passed += expect(InventoryDelta.Quality.AMBIGUOUS, new ItemStack(Items.WHEAT), tagged);
        ItemStack more = tagged.copy();
        more.setCount(2);
        passed += expect(InventoryDelta.Quality.POSITIVE_DELTAS, tagged, more);
        return passed;
    }

    private static int expect(InventoryDelta.Quality wanted, ItemStack before, ItemStack after) {
        var actual = MinecraftInventoryDelta.compare(List.of(before), List.of(after)).quality();
        if (actual != wanted)
            throw new IllegalStateException("Expected " + wanted + " but got " + actual);
        return 1;
    }
}
