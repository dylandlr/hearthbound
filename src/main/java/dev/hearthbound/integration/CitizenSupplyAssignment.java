package dev.hearthbound.integration;

import dev.hearthbound.research.DurableCitizenWorkOrder;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelResource;
import java.io.IOException;
import java.nio.file.Files;
import java.util.UUID;

/** Pre-mutation durable citizen/machine binding for the scripted milling task. */
public final class CitizenSupplyAssignment {
    private CitizenSupplyAssignment() {}
    private static DurableCitizenWorkOrder orders(MinecraftServer server) throws IOException {
        var dir=server.getWorldPath(LevelResource.ROOT).resolve("hearthbound-citizen-milling-workorders");
        Files.createDirectories(dir);
        return new DurableCitizenWorkOrder(dir);
    }
    public static UUID prepareOrReject(MinecraftServer server, UUID citizen,
                                       String dimension, BlockPos mill) {
        try {
            return prepare(server,citizen,dimension,mill);
        } catch(IOException failure) {
            throw new IllegalArgumentException("Could not persist citizen milling assignment",failure);
        }
    }
    public static String machineKey(String dimension,BlockPos mill) {
        return dimension+":"+mill.asLong();
    }
    public static UUID prepare(MinecraftServer server,UUID citizen,String dimension,BlockPos mill)
            throws IOException {
        var key=machineKey(dimension,mill);
        var prepared=orders(server).prepare(citizen,key,"create:milling/wheat",
                "world",dimension,Long.toString(mill.asLong()));
        return prepared.intent().operationId();
    }
    /** Unrecoverable or conflicting assignments must never authorize a mutation. */
    public static boolean isAuthorized(MinecraftServer server,UUID citizen,String dimension,BlockPos mill) {
        try {
            return require(server,citizen,dimension,mill)!=null;
        } catch(IOException | IllegalArgumentException invalid) {
            return false;
        }
    }
    public static UUID require(MinecraftServer server,UUID citizen,String dimension,BlockPos mill)
            throws IOException {
        var key=machineKey(dimension,mill);
        var order=orders(server).recover(citizen,key);
        if(!order.citizenId().equals(citizen)||!order.dimension().equals(dimension)
                || !order.position().equals(Long.toString(mill.asLong()))
                || !order.recipeId().equals("create:milling/wheat"))
            throw new IOException("Mismatched durable milling work order");
        return order.operationId();
    }
}
