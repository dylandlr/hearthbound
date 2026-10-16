package dev.hearthbound.integration;

import dev.hearthbound.research.WorldEvidenceJournal;

/**
 * Stable integration boundary between Create runtime observation and Hearthbound research.
 *
 * The actual Create hook must construct a snapshot only after the server confirms that input was
 * consumed and output was physically produced at the expected machine. Keeping this class free of
 * Create implementation types makes causal/research tests runnable without Minecraft.
 */
public final class CreateProcessingEvidenceAdapter {
    public record VerifiedProcessingSnapshot(
            long tick,
            String levelId,
            String machineType,
            String machinePosition,
            String inputItem,
            int inputCount,
            String outputItem,
            int outputCount,
            String recipeId,
            String physicalEventNonce,
            boolean inputConsumed,
            boolean outputProduced) {}

    private final WorldEvidenceJournal journal;

    public CreateProcessingEvidenceAdapter(WorldEvidenceJournal journal) {
        this.journal = journal;
    }

    public WorldEvidenceJournal.ProcessingEvidence accept(VerifiedProcessingSnapshot snapshot) {
        if (snapshot == null) throw new IllegalArgumentException("snapshot is required");
        if (!snapshot.inputConsumed() || !snapshot.outputProduced()) {
            throw new IllegalArgumentException("Processing is not physically verified");
        }
        if (snapshot.physicalEventNonce() == null || snapshot.physicalEventNonce().isBlank()) {
            throw new IllegalArgumentException("physicalEventNonce is required");
        }

        String evidenceId = String.join(":",
                "create",
                snapshot.levelId(),
                snapshot.machinePosition(),
                snapshot.physicalEventNonce());

        return journal.append(new WorldEvidenceJournal.ProcessingEvidence(
                evidenceId,
                snapshot.tick(),
                snapshot.levelId(),
                snapshot.machineType(),
                snapshot.machinePosition(),
                snapshot.inputItem(),
                snapshot.inputCount(),
                snapshot.outputItem(),
                snapshot.outputCount(),
                snapshot.recipeId(),
                true));
    }
}
