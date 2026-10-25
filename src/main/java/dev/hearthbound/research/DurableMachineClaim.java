package dev.hearthbound.research;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Objects;
import java.util.UUID;

/**
 * Persistent, exclusive machine claim. Machine identity, not citizen identity,
 * is the durable-intent key, so only one unresolved claimant can exist.
 * Claims intentionally cannot expire or be silently transferred.
 */
public final class DurableMachineClaim {
    private final DurableOperationIntents intents;
    public record Claim(UUID claimId, UUID operationId, UUID citizenId, String machineKey) {}
    public DurableMachineClaim(Path existingDirectory) {
        intents = new DurableOperationIntents(Objects.requireNonNull(existingDirectory));
    }
    private static String key(String machineKey) {
        if (machineKey == null || machineKey.isBlank())
            throw new IllegalArgumentException("Missing machine identity");
        return "exclusive-machine/" + machineKey;
    }
    private static String evidence(UUID operationId, UUID citizenId) {
        return Objects.requireNonNull(operationId) + "|" + Objects.requireNonNull(citizenId);
    }
    public DurableOperationIntents.Prepared claim(String machineKey, UUID operationId, UUID citizenId)
            throws IOException {
        return intents.prepare(key(machineKey), evidence(operationId, citizenId));
    }
    public Claim recover(String machineKey) throws IOException {
        var intent = intents.pending(key(machineKey))
                .orElseThrow(() -> new IOException("Machine is not claimed"));
        String[] fields = intent.evidence().split("\\|", -1);
        if (fields.length != 2) throw new IOException("Invalid machine claim");
        try {
            return new Claim(intent.operationId(), UUID.fromString(fields[0]),
                    UUID.fromString(fields[1]), machineKey);
        } catch (IllegalArgumentException failure) {
            throw new IOException("Invalid durable machine claimant", failure);
        }
    }
}
