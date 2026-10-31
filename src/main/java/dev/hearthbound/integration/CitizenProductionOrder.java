package dev.hearthbound.integration;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import java.io.IOException;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.Container;
import net.minecraft.world.entity.npc.Villager;

/** One command for a guarded supply -> real milling -> collection -> stockpile plan. */
public final class CitizenProductionOrder {
    private CitizenProductionOrder() {}

    /**
     * Configures a real citizen for a single production operation. Machinery
     * must be powered separately. Does not create wheat, products or machines.
     */
    public static UUID start(MinecraftServer server, String dimension, UUID citizen,
                             BlockPos millingApproach, BlockPos storageApproach) throws IOException {
        if (server == null || citizen == null || dimension == null
                || millingApproach == null || storageApproach == null)
            throw new IllegalArgumentException("Missing production parameters");
        var level = server.getLevel(net.minecraft.resources.ResourceKey.create(
                net.minecraft.core.registries.Registries.DIMENSION,
                new net.minecraft.resources.ResourceLocation(dimension)));
        if (level == null) throw new IllegalArgumentException("Production dimension not loaded");
        Villager villager = CitizenEmbodiment.find(level,citizen);
        if (villager == null || !villager.isAlive())
            throw new IllegalArgumentException("Citizen must be embodied and alive");
        var record = CitizenRegistrySavedData.get(server).snapshot().stream()
                .filter(entry -> entry.id().equals(citizen)).findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Citizen not registered"));
        if (!"IDLE".equals(record.task()) || !dimension.equals(record.dimension()))
            throw new IllegalStateException("Citizen already assigned or in wrong dimension");
        var data = villager.getPersistentData();
        if (data.getInt("HearthboundWheat") <= 0
                || data.contains("HearthboundMillCollected")
                || data.hasUUID("HearthboundLastStockpileOperation"))
            throw new IllegalStateException("Citizen has no wheat or carries unresolved cargo");
        BlockPos millPos = millingApproach.offset(1,0,0);
        if (!(level.getBlockEntity(millPos) instanceof MillstoneBlockEntity mill)
                || !mill.inputInv.getStackInSlot(0).isEmpty())
            throw new IllegalStateException("Millstone missing or occupied");
        if (!(level.getBlockEntity(storageApproach.offset(1,0,0)) instanceof Container))
            throw new IllegalStateException("Stockpile container missing");
        UUID operation=CitizenSupplyAssignment.prepare(server,citizen,dimension,millPos);
        data.putLong("HearthboundProductionStockpileTarget",storageApproach.asLong());
        CitizenRegistrySavedData.get(server).assignMillSupply(citizen,dimension,
                millingApproach.asLong(),ForgeServerTickObserver.logicalTick(server));
        return operation;
    }
}
