package dev.hearthbound.research;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Objects;
import java.util.UUID;

/**
 * Durable ownership of a citizen work order, prepared before any machine
 * mutation. Its immutable identity survives a server restart.
 */
public final class DurableCitizenWorkOrder {
    private final DurableOperationIntents intents;
    public record Order(UUID operationId, UUID citizenId, String machineKey, String recipeId,
                        String worldId, String dimension, String position) {}
    public DurableCitizenWorkOrder(Path existingDirectory) {
        intents = new DurableOperationIntents(Objects.requireNonNull(existingDirectory));
    }
    private static String key(UUID citizenId, String machineKey) {
        return "citizen-order/" + citizenId + "/" + machineKey;
    }
    private static String encode(UUID citizenId, String machineKey, String recipeId,
                                 String worldId, String dimension, String position) {
        for (String value : new String[]{machineKey, recipeId, worldId, dimension, position})
            if (value == null || value.isBlank() || value.contains("|"))
                throw new IllegalArgumentException("Invalid work order field");
        return citizenId + "|" + recipeId + "|" + worldId + "|" + dimension + "|" + position;
    }
    public DurableOperationIntents.Prepared prepare(UUID citizenId, String machineKey, String recipeId,
                                                     String worldId, String dimension, String position)
            throws IOException {
        Objects.requireNonNull(citizenId);
        return intents.prepare(key(citizenId, machineKey),
                encode(citizenId, machineKey, recipeId, worldId, dimension, position));
    }
    public Order recover(UUID citizenId, String machineKey) throws IOException {
        Objects.requireNonNull(citizenId);
        var pending = intents.pending(key(citizenId, machineKey))
                .orElseThrow(() -> new IOException("Missing durable citizen work order"));
        String[] parts = pending.evidence().split("\\|", -1);
        if (parts.length != 5 || !parts[0].equals(citizenId.toString()))
            throw new IOException("Invalid recovered citizen work order");
        return new Order(pending.operationId(), citizenId, machineKey,
                parts[1], parts[2], parts[3], parts[4]);
    }
}
