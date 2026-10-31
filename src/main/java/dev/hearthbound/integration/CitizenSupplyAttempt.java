package dev.hearthbound.integration;

import dev.hearthbound.research.DurableOperationIntents;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelResource;
import java.io.IOException;
import java.nio.file.Files;
import java.util.UUID;

/**
 * Write-ahead delivery guard. An unresolved attempt is deliberately NOT
 * authorization to repeat a mutation; it must be reconciled by an operator.
 */
public final class CitizenSupplyAttempt {
    private CitizenSupplyAttempt() {}
    private static DurableOperationIntents store(MinecraftServer server) throws IOException {
        var folder=server.getWorldPath(LevelResource.ROOT).resolve("hearthbound-citizen-supply-attempts");
        Files.createDirectories(folder);
        return new DurableOperationIntents(folder);
    }
    public static String key(UUID operation) {return "supply-attempt/"+operation;}
    public static boolean hasAttempt(MinecraftServer server,UUID operation) {
        try {return store(server).pending(key(operation)).isPresent();}
        catch(IOException failure) {return true;} // Corruption must block, not authorize.
    }
    public static UUID begin(MinecraftServer server,UUID operation,UUID citizen,
                             String dimension,BlockPos machine) throws IOException {
        String evidence=operation+"|"+citizen+"|"+dimension+"|"+machine.asLong()+"|wheat=1";
        var prepared=store(server).prepare(key(operation),evidence);
        if(!prepared.newlyCreated())
            throw new IOException("Existing delivery attempt requires reconciliation");
        return prepared.intent().operationId();
    }
}
