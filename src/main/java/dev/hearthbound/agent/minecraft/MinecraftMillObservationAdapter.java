package dev.hearthbound.agent.minecraft;

import dev.hearthbound.agent.v02.HierarchicalTask;
import dev.hearthbound.agent.v02.MillObservation;
import java.util.EnumSet;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.items.IItemHandler;

/** Read-only bridge from the existing First Mill world/NBT contract to agent observation v0.2. */
public final class MinecraftMillObservationAdapter {
    public static final String VERSION = "hearthbound.agent.minecraft-adapter.v0.2";
    private static final String ORDER = "HearthboundMillOrder";
    private static final String HAUL = "HearthboundHaul";

    private MinecraftMillObservationAdapter() {}

    public static MillObservation observe(Villager worker) {
        if (!(worker.level() instanceof ServerLevel level))
            throw new IllegalArgumentException("Server worker required");
        CompoundTag data = worker.getPersistentData();
        if (!data.contains(ORDER, 10)) throw new IllegalArgumentException("Worker has no First Mill order");
        CompoundTag order = data.getCompound(ORDER);
        BlockPos sourcePos = BlockPos.of(order.getLong("Wheat"));
        BlockPos millPos = BlockPos.of(order.getLong("Mill"));
        BlockPos storePos = BlockPos.of(order.getLong("Flour"));

        boolean sourceVisible = level.hasChunkAt(sourcePos)
                && level.getBlockEntity(sourcePos) instanceof BarrelBlockEntity;
        boolean millVisible = level.hasChunkAt(millPos) && level.getBlockEntity(millPos) != null;
        boolean storeVisible = level.hasChunkAt(storePos)
                && level.getBlockEntity(storePos) instanceof BarrelBlockEntity;
        Item flour = BuiltInRegistries.ITEM.get(new ResourceLocation("create", "wheat_flour"));

        int sourceWheat = sourceVisible ? countBarrel((BarrelBlockEntity) level.getBlockEntity(sourcePos), Items.WHEAT) : 0;
        int millWheat = millVisible ? countHandler(level, millPos, Direction.UP, Items.WHEAT) : 0;
        int millFlour = millVisible ? countHandler(level, millPos, Direction.EAST, flour) : 0;
        int storeFlour = storeVisible ? countBarrel((BarrelBlockEntity) level.getBlockEntity(storePos), flour) : 0;

        CompoundTag haul = data.contains(HAUL, 10) ? data.getCompound(HAUL) : new CompoundTag();
        int cargoFlour = "create:wheat_flour".equals(haul.getString("Item")) ? haul.getInt("Cargo") : 0;
        HierarchicalTask task = task(order.getString("State"), cargoFlour);
        EnumSet<HierarchicalTask> mask = EnumSet.of(HierarchicalTask.WAIT);
        if (sourceVisible && sourceWheat > 0 && cargoFlour == 0) mask.add(HierarchicalTask.SUPPLY_MILL);
        if (millVisible && millFlour > 0 && cargoFlour == 0) mask.add(HierarchicalTask.COLLECT_FLOUR);
        if (cargoFlour > 0) mask.add(HierarchicalTask.RETURN_TO_WAIT);

        return new MillObservation(sourceVisible, sourceWheat, millVisible, millWheat, millFlour,
                storeVisible, storeFlour, cargoFlour, order.getInt("TargetFlour"), task,
                isFailure(order.getString("State"), haul.getString("Result")), mask, level.getGameTime());
    }

    private static HierarchicalTask task(String state, int cargoFlour) {
        if (cargoFlour > 0) return HierarchicalTask.RETURN_TO_WAIT;
        return switch (state) {
            case "SUPPLYING_WHEAT", "MILLING" -> HierarchicalTask.SUPPLY_MILL;
            case "COLLECTING_FLOUR" -> HierarchicalTask.COLLECT_FLOUR;
            default -> HierarchicalTask.WAIT;
        };
    }

    private static boolean isFailure(String state, String haulResult) {
        return state.startsWith("MISSING_") || state.endsWith("_DENIED")
                || haulResult.startsWith("MISSING_") || haulResult.startsWith("NO_")
                || haulResult.startsWith("OUTPUT_FULL") || haulResult.startsWith("WRONG_");
    }

    private static int countBarrel(BarrelBlockEntity barrel, Item item) {
        int count = 0;
        for (int slot = 0; slot < barrel.getContainerSize(); slot++)
            if (barrel.getItem(slot).is(item)) count += barrel.getItem(slot).getCount();
        return count;
    }

    private static int countHandler(ServerLevel level, BlockPos pos, Direction side, Item item) {
        IItemHandler handler = level.getBlockEntity(pos)
                .getCapability(ForgeCapabilities.ITEM_HANDLER, side).orElse(null);
        if (handler == null) return 0;
        int count = 0;
        for (int slot = 0; slot < handler.getSlots(); slot++)
            if (handler.getStackInSlot(slot).is(item)) count += handler.getStackInSlot(slot).getCount();
        return count;
    }
}
