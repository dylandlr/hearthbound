package dev.hearthbound.gametest;

import dev.hearthbound.integration.CitizenRegistrySavedData;
import dev.hearthbound.integration.CitizenSupplyAssignment;
import dev.hearthbound.integration.CitizenSupplyAttempt;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtIo;
import net.minecraft.server.MinecraftServer;
import java.io.File;
import java.io.IOException;
import java.util.UUID;

/** Second-JVM recovery assertions for the real citizen delivery work order. */
public final class CitizenSupplyRestartFixture {
    private CitizenSupplyRestartFixture() {}
    public static void write(MinecraftServer server, UUID citizen, String dimension,
                             BlockPos mill, BlockPos villagerPosition, int expectedWheat) throws IOException {
        UUID operation=CitizenSupplyAssignment.require(server,citizen,dimension,mill);
        if(!CitizenSupplyAttempt.hasAttempt(server,operation))
            throw new IOException("Missing write-ahead delivery attempt");
        CompoundTag tag=new CompoundTag();
        tag.putUUID("Citizen",citizen);
        tag.putUUID("Operation",operation);
        tag.putString("Dimension",dimension);
        tag.putLong("Mill",mill.asLong());
        tag.putInt("RemainingWheat",expectedWheat);
        tag.putLong("VillagerPosition",villagerPosition.asLong());
        NbtIo.writeCompressed(tag,new File("citizen-supply-restart-expected.nbt"));
    }
    public static void verify(MinecraftServer server,File expectedFile) throws IOException {
        CompoundTag tag=NbtIo.readCompressed(expectedFile);
        UUID citizen=tag.getUUID("Citizen");
        UUID operation=CitizenSupplyAssignment.require(server,citizen,tag.getString("Dimension"),
                BlockPos.of(tag.getLong("Mill")));
        if(!operation.equals(tag.getUUID("Operation")) || !CitizenSupplyAttempt.hasAttempt(server,operation))
            throw new IOException("Citizen supply operation identity lost on Minecraft restart");
        boolean retained=CitizenRegistrySavedData.get(server).snapshot().stream()
                .anyMatch(c -> c.id().equals(citizen) && c.task().startsWith("MILL_SUPPLY:"));
        if(!retained)
            throw new IOException("Blocked citizen work task did not survive restart");
        var level=server.getLevel(net.minecraft.resources.ResourceKey.create(
                net.minecraft.core.registries.Registries.DIMENSION,
                new net.minecraft.resources.ResourceLocation(tag.getString("Dimension"))));
        if(level==null) throw new IOException("Citizen dimension missing on restart");
        BlockPos millPos=BlockPos.of(tag.getLong("Mill"));
        level.getChunkAt(millPos);
        level.getChunkAt(BlockPos.of(tag.getLong("VillagerPosition")));
        var villager=dev.hearthbound.integration.CitizenEmbodiment.find(level,citizen);
        if(villager==null) throw new IOException("Citizen entity missing after restart");
        var data=villager.getPersistentData();
        if(data.getInt("HearthboundWheat")!=tag.getInt("RemainingWheat")
                || !data.hasUUID("HearthboundLastSupplyOperation")
                || !operation.equals(data.getUUID("HearthboundLastSupplyOperation"))
                || data.getLong("HearthboundLastSupplyMill")!=millPos.asLong())
            throw new IOException("Villager resource balance or delivery receipt changed on restart");
        var machine=level.getBlockEntity(millPos);
        if(!(machine instanceof com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity mill)
                || !mill.inputInv.getStackInSlot(0).is(net.minecraft.world.item.Items.WHEAT)
                || mill.inputInv.getStackInSlot(0).getCount()!=1)
            throw new IOException("Create millstone input did not survive restart");
        // A completed prior delivery has an outstanding second task against
        // the same write-ahead operation. It is unsafe to reinterpret that
        // receipt as permission to replay the second delivery.
        var decision=dev.hearthbound.integration.CitizenSupplyInspection.inspect(
                server,citizen,tag.getString("Dimension"),millPos,villager,mill);
        if(decision!=dev.hearthbound.integration.CitizenSupplyRecovery.Decision.AMBIGUOUS_BLOCKED)
            throw new IOException("Recovered occupied machine must not authorize a repeated delivery");
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_CITIZEN_RESTART_NO_REPLAY_PASS citizen={} operation={} decision={}",
                citizen,operation,decision);
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_CITIZEN_SUPPLY_WORLD_RESTART_PASS citizen={} operation={} wheatRemaining={} millWheat=1",
                citizen,operation,data.getInt("HearthboundWheat"));
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_CITIZEN_SUPPLY_RESTART_PASS citizen={} operation={} pendingTask=true",
                citizen,operation);
    }
}
