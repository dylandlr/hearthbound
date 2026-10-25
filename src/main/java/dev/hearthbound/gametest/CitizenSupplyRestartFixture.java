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
                             BlockPos mill, int expectedWheat) throws IOException {
        UUID operation=CitizenSupplyAssignment.require(server,citizen,dimension,mill);
        if(!CitizenSupplyAttempt.hasAttempt(server,operation))
            throw new IOException("Missing write-ahead delivery attempt");
        CompoundTag tag=new CompoundTag();
        tag.putUUID("Citizen",citizen);
        tag.putUUID("Operation",operation);
        tag.putString("Dimension",dimension);
        tag.putLong("Mill",mill.asLong());
        tag.putInt("RemainingWheat",expectedWheat);
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
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_CITIZEN_SUPPLY_RESTART_PASS citizen={} operation={} pendingTask=true",
                citizen,operation);
    }
}
