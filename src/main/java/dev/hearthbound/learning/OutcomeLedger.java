package dev.hearthbound.learning;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/**
 * Server-authoritative causal credit ledger.
 *
 * Decisions are registered before their outcomes occur. A physical evidence id can be
 * consumed exactly once, preventing duplicated rewards from replayed world events.
 */
public final class OutcomeLedger {
    public record RewardVector(double personal, double colony, double research) {
        public RewardVector {
            if (!Double.isFinite(personal) || !Double.isFinite(colony) || !Double.isFinite(research)) {
                throw new IllegalArgumentException("Reward values must be finite");
            }
        }

        public RewardVector scale(double factor) {
            if (!Double.isFinite(factor) || factor < 0.0) {
                throw new IllegalArgumentException("Scale factor must be finite and non-negative");
            }
            return new RewardVector(personal * factor, colony * factor, research * factor);
        }
    }

    public record Decision(String decisionId, String agentId, long tick) {
        public Decision {
            requireText(decisionId, "decisionId");
            requireText(agentId, "agentId");
            if (tick < 0) throw new IllegalArgumentException("tick must be non-negative");
        }
    }

    private final Map<String, Decision> decisions = new LinkedHashMap<>();
    private final Map<String, Map<String, RewardVector>> consumedEvidence = new LinkedHashMap<>();

    public synchronized void registerDecision(Decision decision) {
        Objects.requireNonNull(decision, "decision");
        Decision previous = decisions.putIfAbsent(decision.decisionId(), decision);
        if (previous != null && !previous.equals(decision)) {
            throw new IllegalStateException("Decision id already registered with different data: " + decision.decisionId());
        }
    }

    /**
     * Credits a verified physical event among contributing decisions.
     *
     * @param evidenceId unique id produced by the world-event journal
     * @param eventTick tick when the verified physical outcome occurred
     * @param contributionWeights decision id -> positive contribution weight
     * @param totalReward reward domains to distribute
     * @return agent id -> allocated reward vector
     */
    public synchronized Map<String, RewardVector> credit(
            String evidenceId,
            long eventTick,
            Map<String, Double> contributionWeights,
            RewardVector totalReward) {

        requireText(evidenceId, "evidenceId");
        Objects.requireNonNull(contributionWeights, "contributionWeights");
        Objects.requireNonNull(totalReward, "totalReward");
        if (eventTick < 0) throw new IllegalArgumentException("eventTick must be non-negative");
        if (consumedEvidence.containsKey(evidenceId)) {
            throw new IllegalStateException("Evidence already consumed: " + evidenceId);
        }
        if (contributionWeights.isEmpty()) {
            throw new IllegalArgumentException("At least one contributor is required");
        }

        double totalWeight = 0.0;
        Map<String, Decision> resolved = new LinkedHashMap<>();
        for (Map.Entry<String, Double> entry : contributionWeights.entrySet()) {
            String decisionId = entry.getKey();
            Double weight = entry.getValue();
            requireText(decisionId, "decisionId");
            if (weight == null || !Double.isFinite(weight) || weight <= 0.0) {
                throw new IllegalArgumentException("Contribution weights must be finite and positive");
            }

            Decision decision = decisions.get(decisionId);
            if (decision == null) {
                throw new IllegalArgumentException("Unknown contributing decision: " + decisionId);
            }
            if (decision.tick() > eventTick) {
                throw new IllegalArgumentException("Future decision cannot cause past evidence: " + decisionId);
            }
            resolved.put(decisionId, decision);
            totalWeight += weight;
        }

        Map<String, RewardVector> perAgent = new LinkedHashMap<>();
        for (Map.Entry<String, Double> entry : contributionWeights.entrySet()) {
            Decision decision = resolved.get(entry.getKey());
            double fraction = entry.getValue() / totalWeight;
            RewardVector share = totalReward.scale(fraction);
            perAgent.merge(decision.agentId(), share, OutcomeLedger::add);
        }

        consumedEvidence.put(evidenceId, Map.copyOf(perAgent));
        return Map.copyOf(perAgent);
    }

    public synchronized boolean hasConsumedEvidence(String evidenceId) {
        return consumedEvidence.containsKey(evidenceId);
    }

    public synchronized int registeredDecisionCount() {
        return decisions.size();
    }

    private static RewardVector add(RewardVector a, RewardVector b) {
        return new RewardVector(
                a.personal() + b.personal(),
                a.colony() + b.colony(),
                a.research() + b.research());
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
    }
}
