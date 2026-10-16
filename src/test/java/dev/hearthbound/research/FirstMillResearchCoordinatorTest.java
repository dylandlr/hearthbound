package dev.hearthbound.research;

import dev.hearthbound.integration.CreateProcessingEvidenceAdapter;
import dev.hearthbound.learning.OutcomeLedger;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

final class FirstMillResearchCoordinatorTest {
    @Test
    void verifiedMillingCreatesKnowledgeThenTeachingSpreadsIt() {
        OutcomeLedger outcomeLedger = new OutcomeLedger();
        WorldEvidenceJournal evidenceJournal = new WorldEvidenceJournal();
        TechKnowledgeLedger knowledgeLedger = new TechKnowledgeLedger();
        FirstMillResearchCoordinator coordinator =
                new FirstMillResearchCoordinator(outcomeLedger, evidenceJournal, knowledgeLedger);
        CreateProcessingEvidenceAdapter adapter =
                new CreateProcessingEvidenceAdapter(evidenceJournal);

        coordinator.beginExperiment(new FirstMillResearchCoordinator.Experiment(
                "sable-wheat-001",
                "sable",
                100L,
                "create:milling/wheat"));

        WorldEvidenceJournal.ProcessingEvidence evidence = adapter.accept(
                new CreateProcessingEvidenceAdapter.VerifiedProcessingSnapshot(
                        140L,
                        "minecraft:overworld",
                        "create:millstone",
                        "12,64,-8",
                        "minecraft:wheat",
                        1,
                        "create:wheat_flour",
                        1,
                        "create:milling/wheat",
                        "physical-140-12-64--8",
                        true,
                        true));

        FirstMillResearchCoordinator.ResearchOutcome outcome =
                coordinator.resolveVerifiedProcessing("sable-wheat-001", evidence.evidenceId(), Map.of());

        assertEquals("create:milling/wheat", outcome.recipeId());
        assertTrue(knowledgeLedger.knows("sable", "create:milling/wheat"));
        assertTrue(outcome.leadKnowledge().confidence() >= 0.35);

        TechKnowledgeLedger.Knowledge taught =
                coordinator.teach("sable", "iven", "create:milling/wheat");

        assertEquals(TechKnowledgeLedger.Source.TAUGHT, taught.source());
        assertEquals("sable", taught.teacherAgentId());
        assertTrue(knowledgeLedger.knows("iven", "create:milling/wheat"));
    }

    @Test
    void replayedPhysicalEvidenceCannotRewardTwice() {
        OutcomeLedger outcomeLedger = new OutcomeLedger();
        WorldEvidenceJournal journal = new WorldEvidenceJournal();
        TechKnowledgeLedger knowledge = new TechKnowledgeLedger();
        FirstMillResearchCoordinator coordinator =
                new FirstMillResearchCoordinator(outcomeLedger, journal, knowledge);
        CreateProcessingEvidenceAdapter adapter = new CreateProcessingEvidenceAdapter(journal);

        coordinator.beginExperiment(new FirstMillResearchCoordinator.Experiment(
                "exp", "sable", 1L, "create:milling/wheat"));

        WorldEvidenceJournal.ProcessingEvidence evidence = adapter.accept(
                new CreateProcessingEvidenceAdapter.VerifiedProcessingSnapshot(
                        2L, "minecraft:overworld", "create:millstone", "0,64,0",
                        "minecraft:wheat", 1, "create:wheat_flour", 1,
                        "create:milling/wheat", "nonce", true, true));

        coordinator.resolveVerifiedProcessing("exp", evidence.evidenceId(), Map.of());

        IllegalStateException replay = assertThrows(
                IllegalStateException.class,
                () -> coordinator.resolveVerifiedProcessing("exp", evidence.evidenceId(), Map.of()));
        assertTrue(replay.getMessage().contains("already consumed"));
    }

    @Test
    void observationWithoutConsumedInputAndProducedOutputIsRejected() {
        WorldEvidenceJournal journal = new WorldEvidenceJournal();
        CreateProcessingEvidenceAdapter adapter = new CreateProcessingEvidenceAdapter(journal);

        assertThrows(IllegalArgumentException.class, () -> adapter.accept(
                new CreateProcessingEvidenceAdapter.VerifiedProcessingSnapshot(
                        2L, "minecraft:overworld", "create:millstone", "0,64,0",
                        "minecraft:wheat", 1, "create:wheat_flour", 1,
                        "create:milling/wheat", "nonce", false, true)));

        assertEquals(0, journal.size());
    }

    @Test
    void futureContributorDecisionIsRejected() {
        OutcomeLedger ledger = new OutcomeLedger();
        ledger.registerDecision(new OutcomeLedger.Decision("future", "hauler", 50L));

        assertThrows(IllegalArgumentException.class, () -> ledger.credit(
                "evidence", 40L, Map.of("future", 1.0),
                new OutcomeLedger.RewardVector(1, 1, 1)));
    }
}
