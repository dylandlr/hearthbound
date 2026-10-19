package dev.hearthbound.research;

/** Deterministic, LLM-free student initiative baseline; inputs are local only. */
public final class LearningRequestPolicy {
    public static final int VERSION = 1;
    public enum Action { REQUEST, DEFER }
    public record Observation(int version, double curiosity, double confidence,
                              double need, boolean recipeKnown,
                              boolean teacherVisible, boolean alreadyRequested) {
        public Observation {
            if (version != VERSION) throw new IllegalArgumentException("Wrong schema");
            for (double n : new double[]{curiosity, confidence, need})
                if (!Double.isFinite(n) || n < 0 || n > 1)
                    throw new IllegalArgumentException("Observation must be in [0,1]");
        }
    }
    public Action select(Observation o) {
        if (o == null) throw new IllegalArgumentException("Observation missing");
        if (o.recipeKnown() || !o.teacherVisible() || o.alreadyRequested()) return Action.DEFER;
        // Uncertainty about a locally observed recipe and own learning motivation
        // determine initiative; this is a transparent baseline, not trained RL.
        return .5 * o.curiosity() + .35 * o.need() + .15 * (1-o.confidence()) >= .42
                ? Action.REQUEST : Action.DEFER;
    }
}
