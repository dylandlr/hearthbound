package dev.hearthbound.research;

import dev.hearthbound.learning.OutcomeLedger;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/**
 * Connects verified First Mill outcomes to causal credit and emergent recipe knowledge.
 */
public final class FirstMillResearchCoordinator {
    public record Experiment(
            String experimentId,
            String leadAgentId,
            long decisionTick,
            String intendedRecipeId) {}

    public record ResearchOutcome(
            String evidenceId,
            String recipeId,
            Map<String, OutcomeLedger.RewardVector> rewards,
            TechKnowledgeLedger.Knowledge leadKnowledge) {}

    private final OutcomeLedger outcomeLedger;
    private final WorldEvidenceJournal evidenceJournal;
    private final TechKnowledgeLedger knowledgeLedger;
    private final Map<String, Experiment> experiments = new LinkedHashMap<>();

    public FirstMillResearchCoordinator(
            OutcomeLedger outcomeLedger,
            WorldEvidenceJournal evidenceJournal,
            TechKnowledgeLedger knowledgeLedger) {
        this.outcomeLedger = Objects.requireNonNull(outcomeLedger);
        this.evidenceJournal = Objects.requireNonNull(evidenceJournal);
        this.knowledgeLedger = Objects.requireNonNull(knowledgeLedger);
    }

    public synchronized void beginExperiment(Experiment experiment) {
        Objects.requireNonNull(experiment, "experiment");
        requireText(experiment.experimentId(), "experimentId");
        requireText(experiment.leadAgentId(), "leadAgentId");
        requireText(experiment.intendedRecipeId(), "intendedRecipeId");
        if (experiment.decisionTick() < 0) throw new IllegalArgumentException("decisionTick must be non-negative");

        Experiment previous = experiments.putIfAbsent(experiment.experimentId(), experiment);
        if (previous != null && !previous.equals(experiment)) {
            throw new IllegalStateException("Experiment id already exists with different data");
        }

        outcomeLedger.registerDecision(new OutcomeLedger.Decision(
                experimentDecisionId(experiment.experimentId()),
                experiment.leadAgentId(),
                experiment.decisionTick()));
    }

    public ResearchOutcome resolveVerifiedProcessing(
            String experimentId,
            String evidenceId,
            Map<String, Double> additionalDecisionWeights) {

        Experiment experiment = requireExperiment(experimentId);
        WorldEvidenceJournal.ProcessingEvidence evidence = evidenceJournal.require(evidenceId);

        if (!experiment.intendedRecipeId().equals(evidence.recipeId())) {
            throw new IllegalArgumentException(
                    "Verified recipe " + evidence.recipeId() +
                    " does not match experiment intent " + experiment.intendedRecipeId());
        }

        Map<String, Double> weights = new LinkedHashMap<>();
        weights.put(experimentDecisionId(experimentId), 1.0);
        if (additionalDecisionWeights != null) {
            for (Map.Entry<String, Double> entry : additionalDecisionWeights.entrySet()) {
                weights.merge(entry.getKey(), entry.getValue(), Double::sum);
            }
        }

        OutcomeLedger.RewardVector totalReward = rewardFor(evidence);
        Map<String, OutcomeLedger.RewardVector> rewards =
                outcomeLedger.credit(evidence.evidenceId(), evidence.tick(), weights, totalReward);

        OutcomeLedger.RewardVector leadReward =
                rewards.getOrDefault(experiment.leadAgentId(), new OutcomeLedger.RewardVector(0, 0, 0));

        TechKnowledgeLedger.Knowledge knowledge = knowledgeLedger.discover(
                experiment.leadAgentId(),
                evidence.recipeId(),
                evidence.evidenceId(),
                leadReward.research());

        return new ResearchOutcome(
                evidence.evidenceId(),
                evidence.recipeId(),
                rewards,
                knowledge);
    }

    public TechKnowledgeLedger.Knowledge teach(
            String teacherAgentId,
            String studentAgentId,
            String recipeId) {
        return knowledgeLedger.teach(teacherAgentId, studentAgentId, recipeId);
    }

    private static OutcomeLedger.RewardVector rewardFor(WorldEvidenceJournal.ProcessingEvidence evidence) {
        double productionScale = Math.min(3.0, 1.0 + Math.log1p(evidence.outputCount()));
        return new OutcomeLedger.RewardVector(
                0.5 * productionScale,
                0.8 * productionScale,
                1.0 * productionScale);
    }

    private synchronized Experiment requireExperiment(String experimentId) {
        Experiment experiment = experiments.get(experimentId);
        if (experiment == null) throw new IllegalArgumentException("Unknown experiment: " + experimentId);
        return experiment;
    }

    private static String experimentDecisionId(String experimentId) {
        return "experiment:" + experimentId;
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
    }
}
