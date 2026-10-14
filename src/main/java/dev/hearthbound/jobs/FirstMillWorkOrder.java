package dev.hearthbound.jobs;

import dev.hearthbound.HearthboundMod;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.util.List;

/** First playable, opt-in, persistent job scheduler. Villager remains server-authoritative. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID)
public final class FirstMillWorkOrder {
    private static final String ROOT = "HearthboundMillOrder";
    private FirstMillWorkOrder() {}

    public static int start(CommandSourceStack source, BlockPos wheat, BlockPos mill, BlockPos flour) {
        ServerLevel level = source.getLevel();
        if (wheat.equals(mill) || wheat.equals(flour) || mill.equals(flour)
                || !level.hasChunkAt(wheat) || !level.hasChunkAt(mill) || !level.hasChunkAt(flour)
                || !(level.getBlockEntity(wheat) instanceof BarrelBlockEntity)
                || !(level.getBlockEntity(flour) instanceof BarrelBlockEntity)
                || !level.getBlockState(mill).is(BuiltInRegistries.BLOCK.get(
                        new ResourceLocation("create", "millstone")))) {
            source.sendFailure(Component.literal("Work order needs two loaded barrels and a Create millstone."));
            return 0;
        }
        List<Villager> sable = level.getEntitiesOfClass(Villager.class,
                new AABB(source.getPosition(), source.getPosition()).inflate(32),
                v -> v.getTags().contains("hearthbound.sable")
                        && !v.getPersistentData().contains(ROOT, 10));
        if (sable.isEmpty()) {
            source.sendFailure(Component.literal("No unassigned Sable within 32 blocks."));
            return 0;
        }
        Villager worker = sable.get(0);
        CompoundTag order = new CompoundTag();
        order.putLong("Wheat", wheat.asLong());
        order.putLong("Mill", mill.asLong());
        order.putLong("Flour", flour.asLong());
        order.putBoolean("Enabled", true);
        order.putString("State", "WAITING");
        worker.getPersistentData().put(ROOT, order);
        source.sendSuccess(() -> Component.literal("First Mill work order enabled for Sable."), false);
        return 1;
    }

    public static int stop(CommandSourceStack source) {
        List<Villager> sable = source.getLevel().getEntitiesOfClass(Villager.class,
                new AABB(source.getPosition(), source.getPosition()).inflate(32),
                v -> v.getTags().contains("hearthbound.sable")
                        && v.getPersistentData().contains(ROOT, 10));
        if (sable.isEmpty()) return 0;
        // Stop scheduling new jobs; never erase cargo from an active haul.
        sable.get(0).getPersistentData().remove(ROOT);
        source.sendSuccess(() -> Component.literal("First Mill scheduling stopped; existing haul retained."), false);
        return 1;
    }

    @SubscribeEvent
    public static void tick(LivingEvent.LivingTickEvent event) {
        Entity entity = event.getEntity();
        if (!(entity instanceof Villager villager) || entity.level().isClientSide()
                || villager.tickCount % 40 != 0
                || !villager.getPersistentData().contains(ROOT, 10)
                || !(entity.level() instanceof ServerLevel level)) return;
        CompoundTag data = villager.getPersistentData();
        CompoundTag order = data.getCompound(ROOT);
        if (!order.getBoolean("Enabled") || data.contains("HearthboundHaul", 10)) return;
        BlockPos wheat = BlockPos.of(order.getLong("Wheat"));
        BlockPos mill = BlockPos.of(order.getLong("Mill"));
        BlockPos flour = BlockPos.of(order.getLong("Flour"));
        if (!level.hasChunkAt(wheat) || !level.hasChunkAt(mill) || !level.hasChunkAt(flour)) {
            order.putString("State", "WAITING_FOR_CHUNKS");
            return;
        }
        if (!(level.getBlockEntity(wheat) instanceof BarrelBlockEntity supply)
                || !(level.getBlockEntity(flour) instanceof BarrelBlockEntity)
                || !level.getBlockState(mill).is(BuiltInRegistries.BLOCK.get(
                        new ResourceLocation("create", "millstone")))) {
            order.putString("State", "MISSING_STATION");
            return;
        }
        // Prioritize finished goods. Otherwise supply up to four wheat.
        if (hasFlourOutput(level, mill)) {
            if (BarrelHaulController.assignFlourCitizen(villager, mill, flour, 1))
                order.putString("State", "COLLECTING_FLOUR");
            return;
        }
        // Do not queue fresh deliveries while wheat is still in the millstone.\n        // This avoids a citizen collecting excess wheat and stalling with cargo.\n        if (hasMillInput(level, mill)) {\n            order.putString("State", "MILLING");\n            return;\n        }\n        int wheatCount = 0;
        for (int i = 0; i < supply.getContainerSize(); i++)
            if (supply.getItem(i).is(Items.WHEAT)) wheatCount += supply.getItem(i).getCount();
        if (wheatCount > 0) {
            if (BarrelHaulController.assignCitizen(villager, wheat, mill, Math.min(4, wheatCount)))
                order.putString("State", "SUPPLYING_WHEAT");
        } else order.putString("State", "WAITING_FOR_WHEAT");
    }

    private static boolean hasMillInput(ServerLevel level, BlockPos pos) {
        var entity = level.getBlockEntity(pos);
        if (entity == null) return false;
        var handler = entity.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.ITEM_HANDLER,
                net.minecraft.core.Direction.UP).orElse(null);
        if (handler == null) return false;
        for (int i = 0; i < handler.getSlots(); i++)
            if (handler.getStackInSlot(i).is(Items.WHEAT)) return true;
        return false;
    }

    private static boolean hasFlourOutput(ServerLevel level, BlockPos pos) {
        var entity = level.getBlockEntity(pos);
        if (entity == null) return false;
        var handler = entity.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.ITEM_HANDLER,
                net.minecraft.core.Direction.EAST).orElse(null);
        if (handler == null) return false;
        var flour = BuiltInRegistries.ITEM.get(new ResourceLocation("create", "wheat_flour"));
        for (int i = 0; i < handler.getSlots(); i++)
            if (handler.getStackInSlot(i).is(flour)) return true;
        return false;
    }
}
