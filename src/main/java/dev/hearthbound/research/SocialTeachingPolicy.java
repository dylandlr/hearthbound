package dev.hearthbound.research;

/**
 * LLM-free hierarchical social teaching baseline (v1).
 * All inputs must be supplied from a citizen's local observation or personal memory.
 * Does not inspect world state, student inventories, or global tech unlocks.
 */
public final class SocialTeachingPolicy {
    public static final int SCHEMA_VERSION = 1;
    public enum Action { TEACH, DEFER, REST }
    public record Observation(int schemaVersion, double cooperation,
                              double confidence, double familiarity,
                              double urgency, double fatigue,
                              boolean studentVisible, boolean recipeKnown,
                              boolean studentRequestsLearning) {
        public Observation {
            if (schemaVersion != SCHEMA_VERSION)
                throw new IllegalArgumentException("Unsupported teaching observation version");
            for (double value : new double[]{cooperation, confidence, familiarity, urgency, fatigue}) {
                if (!Double.isFinite(value) || value < 0 || value > 1)
                    throw new IllegalArgumentException("Teaching observations must be finite in [0,1]");
            }
        }
    }
    public record Choice(Action action, double score, String reason) {}

    public Choice select(Observation o) {
        if (o == null) throw new IllegalArgumentException("Observation required");
        if (!o.recipeKnown() || !o.studentVisible())
            return new Choice(Action.DEFER, 0, "No locally eligible teaching opportunity");
        if (o.fatigue() >= 0.85)
            return new Choice(Action.REST, o.fatigue(), "Exhausted");
        // Explicit utility tradeoff: social drive, familiarity and urgent colony need
        // compete against cost of effort and imperfect confidence.
        double benefit = 0.30 * o.cooperation() + 0.25 * o.familiarity()
                + 0.25 * o.urgency() + 0.20 * o.confidence()
                + (o.studentRequestsLearning() ? 0.15 : 0);
        double cost = 0.30 + 0.45 * o.fatigue();
        return benefit >= cost
                ? new Choice(Action.TEACH, benefit - cost, "Share personally known technology")
                : new Choice(Action.DEFER, cost - benefit, "Teaching opportunity not worthwhile now");
    }
}
