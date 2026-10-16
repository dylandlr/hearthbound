package dev.hearthbound.research;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/**
 * Per-citizen experiential technology knowledge.
 *
 * A recipe is not globally unlocked by script. Citizens first acquire verified evidence,
 * then knowledge can spread socially through teaching.
 */
public final class TechKnowledgeLedger {
    public enum Source {
        DIRECT_EXPERIMENT,
        TAUGHT
    }

    public record Knowledge(
            String agentId,
            String recipeId,
            double confidence,
            Source source,
            String provenanceEvidenceId,
            String teacherAgentId) {

        public Knowledge {
            requireText(agentId, "agentId");
            requireText(recipeId, "recipeId");
            Objects.requireNonNull(source, "source");
            if (!Double.isFinite(confidence) || confidence <= 0.0 || confidence > 1.0) {
                throw new IllegalArgumentException("confidence must be in (0, 1]");
            }
            if (source == Source.DIRECT_EXPERIMENT) {
                requireText(provenanceEvidenceId, "provenanceEvidenceId");
            }
            if (source == Source.TAUGHT) {
                requireText(teacherAgentId, "teacherAgentId");
            }
        }
    }

    private final Map<String, Map<String, Knowledge>> knowledge = new LinkedHashMap<>();

    public synchronized Knowledge discover(
            String agentId,
            String recipeId,
            String evidenceId,
            double researchReward) {

        requireText(evidenceId, "evidenceId");
        double confidence = clamp(0.35 + Math.max(0.0, researchReward) * 0.15, 0.35, 1.0);
        Knowledge discovered = new Knowledge(
                agentId, recipeId, confidence, Source.DIRECT_EXPERIMENT, evidenceId, null);
        upsert(discovered);
        return require(agentId, recipeId);
    }

    public synchronized Knowledge teach(String teacherAgentId, String studentAgentId, String recipeId) {
        Knowledge teacher = require(teacherAgentId, recipeId);
        double transmitted = clamp(teacher.confidence() * 0.80, 0.15, 0.95);
        Knowledge taught = new Knowledge(
                studentAgentId,
                recipeId,
                transmitted,
                Source.TAUGHT,
                teacher.provenanceEvidenceId(),
                teacherAgentId);
        upsert(taught);
        return require(studentAgentId, recipeId);
    }

    public synchronized boolean knows(String agentId, String recipeId) {
        Map<String, Knowledge> byRecipe = knowledge.get(agentId);
        return byRecipe != null && byRecipe.containsKey(recipeId);
    }

    public synchronized Knowledge require(String agentId, String recipeId) {
        Map<String, Knowledge> byRecipe = knowledge.get(agentId);
        Knowledge result = byRecipe == null ? null : byRecipe.get(recipeId);
        if (result == null) {
            throw new IllegalArgumentException(agentId + " does not know recipe " + recipeId);
        }
        return result;
    }

    private void upsert(Knowledge candidate) {
        Map<String, Knowledge> byRecipe =
                knowledge.computeIfAbsent(candidate.agentId(), ignored -> new LinkedHashMap<>());
        Knowledge previous = byRecipe.get(candidate.recipeId());
        if (previous == null || candidate.confidence() > previous.confidence()) {
            byRecipe.put(candidate.recipeId(), candidate);
        }
    }

    private static double clamp(double value, double min, double max) {
        return Math.max(min, Math.min(max, value));
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
    }
}
