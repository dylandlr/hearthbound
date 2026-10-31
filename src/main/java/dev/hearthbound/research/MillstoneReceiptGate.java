package dev.hearthbound.research;

import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * Pure-Java ingress gate between a server-side Create completion hook and the durable journal.
 * This is NOT a Create event listener. Only authoritative server code may supply an InputProof.
 */
public final class MillstoneReceiptGate {
    public record Stack(String itemId, int count) {
        public Stack {
            if (itemId == null || !itemId.matches("[a-z0-9_.-]+:[a-z0-9_./-]+") || count <= 0)
                throw new IllegalArgumentException("Invalid item stack");
        }
    }
    public record InputProof(UUID operationId, String worldId, String dimension,
                             String machinePosition, String recipeId, List<Stack> consumed) {
        public InputProof {
            Objects.requireNonNull(operationId);
            Objects.requireNonNull(worldId);
            Objects.requireNonNull(dimension);
            Objects.requireNonNull(machinePosition);
            Objects.requireNonNull(recipeId);
            consumed = List.copyOf(consumed);
        }
    }
    public record Completion(String source, UUID operationId, String worldId, String dimension,
                             String machinePosition, String recipeId, List<Stack> produced) {
        public Completion {
            Objects.requireNonNull(source);
            Objects.requireNonNull(operationId);
            Objects.requireNonNull(worldId);
            Objects.requireNonNull(dimension);
            Objects.requireNonNull(machinePosition);
            Objects.requireNonNull(recipeId);
            produced = List.copyOf(produced);
        }
    }
    public record Accepted(UUID operationId, List<Stack> consumed, List<Stack> produced) {}

    /** Rejects event-only completions: inputs must be proven by server-owned operation state. */
    public static Accepted validate(InputProof proof, Completion completion) {
        if (proof == null) throw new IllegalArgumentException("No authoritative input proof");
        Objects.requireNonNull(completion);
        if (!"MILLSTONE".equals(completion.source())) throw new IllegalArgumentException("Wrong machine source");
        if (!proof.operationId().equals(completion.operationId()) ||
            !proof.worldId().equals(completion.worldId()) ||
            !proof.dimension().equals(completion.dimension()) ||
            !proof.machinePosition().equals(completion.machinePosition()) ||
            !proof.recipeId().equals(completion.recipeId()))
            throw new IllegalArgumentException("Completion does not match persisted operation");
        if (proof.consumed().isEmpty() || completion.produced().isEmpty())
            throw new IllegalArgumentException("Missing actual inputs or outputs");
        return new Accepted(proof.operationId(), proof.consumed(), completion.produced());
    }
    private MillstoneReceiptGate() {}
}
