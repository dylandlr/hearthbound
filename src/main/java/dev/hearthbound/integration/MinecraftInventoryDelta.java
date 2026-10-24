package dev.hearthbound.integration;

import dev.hearthbound.research.InventoryDelta;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.registries.ForgeRegistries;

/** Forge adapter: compares full Minecraft item + NBT identity, not only registry IDs. */
public final class MinecraftInventoryDelta {
    private MinecraftInventoryDelta() {}

    public static InventoryDelta.Result compare(List<ItemStack> before, List<ItemStack> after) {
        if (before == null || after == null || before.size() != after.size())
            throw new IllegalArgumentException("Invalid snapshot sizes");
        List<InventoryDelta.Stack> increases = new ArrayList<>();
        boolean ambiguous = false;
        for (int slot = 0; slot < before.size(); slot++) {
            ItemStack old = before.get(slot), now = after.get(slot);
            if (old == null || now == null) throw new IllegalArgumentException("Null ItemStack");
            if (old.isEmpty() && now.isEmpty()) continue;
            if (old.isEmpty()) {
                increases.add(new InventoryDelta.Stack(ForgeRegistries.ITEMS.getKey(now.getItem()).toString(), now.getCount()));
            } else if (now.isEmpty()) {
                ambiguous = true;
            } else if (!ItemStack.isSameItemSameTags(old, now)) {
                ambiguous = true;
            } else {
                int countDiff = now.getCount() - old.getCount();
                if (countDiff < 0) ambiguous = true;
                if (countDiff > 0)
                    increases.add(new InventoryDelta.Stack(ForgeRegistries.ITEMS.getKey(now.getItem()).toString(), countDiff));
            }
        }
        return new InventoryDelta.Result(ambiguous ? InventoryDelta.Quality.AMBIGUOUS
                : increases.isEmpty() ? InventoryDelta.Quality.NONE_OBSERVED
                : InventoryDelta.Quality.POSITIVE_DELTAS, increases);
    }
}
