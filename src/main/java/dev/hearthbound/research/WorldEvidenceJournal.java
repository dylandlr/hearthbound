package dev.hearthbound.research;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/**
 * Append-only journal of server-verified physical outcomes.
 *
 * Persistence is deliberately separated from event detection. The current implementation is
 * in-memory; Minecraft SavedData storage can replace the backing store without changing the
 * learning contract.
 */
public final class WorldEvidenceJournal {
    public record ProcessingEvidence(
            String evidenceId,
            long tick,
            String levelId,
            String machineType,
            String machinePosition,
            String inputItem,
            int inputCount,
            String outputItem,
            int outputCount,
            String recipeId,
            boolean physicallyVerified) {

        public ProcessingEvidence {
            requireText(evidenceId, "evidenceId");
            requireText(levelId, "levelId");
            requireText(machineType, "machineType");
            requireText(machinePosition, "machinePosition");
            requireText(inputItem, "inputItem");
            requireText(outputItem, "outputItem");
            requireText(recipeId, "recipeId");
            if (tick < 0) throw new IllegalArgumentException("tick must be non-negative");
            if (inputCount <= 0 || outputCount <= 0) {
                throw new IllegalArgumentException("input/output counts must be positive");
            }
        }
    }

    private final Map<String, ProcessingEvidence> entries = new LinkedHashMap<>();

    public synchronized ProcessingEvidence append(ProcessingEvidence evidence) {
        Objects.requireNonNull(evidence, "evidence");
        if (!evidence.physicallyVerified()) {
            throw new IllegalArgumentException("Unverified machine observations are not research evidence");
        }
        ProcessingEvidence previous = entries.putIfAbsent(evidence.evidenceId(), evidence);
        if (previous != null) {
            if (!previous.equals(evidence)) {
                throw new IllegalStateException("Evidence id collision: " + evidence.evidenceId());
            }
            return previous;
        }
        return evidence;
    }

    public synchronized ProcessingEvidence require(String evidenceId) {
        ProcessingEvidence evidence = entries.get(evidenceId);
        if (evidence == null) throw new IllegalArgumentException("Unknown evidence: " + evidenceId);
        return evidence;
    }

    public synchronized int size() {
        return entries.size();
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
    }
}
