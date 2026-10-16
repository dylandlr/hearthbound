package dev.hearthbound.research;

import java.util.Comparator;
import java.util.List;
import java.util.Objects;

/**
 * Versioned, deterministic learning-task baseline.
 * Observations are partial: the policy only consumes information visible to
 * the citizen and never consults omniscient Minecraft world state.
 */
public final class LearningDecisionPolicy {
    public static final int SCHEMA_VERSION = 1;
    public enum Action { OBSERVE_BOOK, OBSERVE_CITIZEN, INNOVATE, EXPLOIT, REST }
    public record Observation(
            int schemaVersion,
            double curiosity,
            double literacy,
            double fatigue,
            double hunger,
            double colonyUrgency,
            double theory,
            double competence,
            boolean accessibleBook,
            boolean accessibleTeacher,
            boolean experimentAvailable,
            boolean productionAvailable) {
        public Observation {
            if (schemaVersion != SCHEMA_VERSION)
                throw new IllegalArgumentException("Unsupported observation schema");
            for (double x : new double[]{curiosity,literacy,fatigue,hunger,
                    colonyUrgency,theory,competence}) {
                if (!Double.isFinite(x) || x < 0 || x > 1)
                    throw new IllegalArgumentException("Observation values must be in [0,1]");
            }
        }
    }
    public record Choice(Action action, double score, String rationale) {}

    /**
     * Simple transparent baseline; weights are hypotheses for evaluation, not
     * learned parameters or empirically validated game balance.
     */
    public Choice select(Observation o) {
        Objects.requireNonNull(o);
        double distress = Math.max(o.hunger(), o.fatigue());
        List<Choice> options = new java.util.ArrayList<>();
        options.add(new Choice(Action.REST, 0.12 + distress, "Restore needs"));
        if (o.accessibleBook()) options.add(new Choice(Action.OBSERVE_BOOK,
                (1-o.theory()) * (0.3 + 0.4*o.literacy() + 0.3*o.curiosity())
                        - 0.5*distress, "Read accessible technical material"));
        if (o.accessibleTeacher()) options.add(new Choice(Action.OBSERVE_CITIZEN,
                (1-o.theory()) * (0.25+0.35*o.curiosity())
                        - 0.4*distress, "Learn socially"));
        if (o.experimentAvailable()) options.add(new Choice(Action.INNOVATE,
                (1-o.competence()) * (0.25+0.45*o.curiosity()+0.2*o.theory())
                        - 0.6*distress, "Run a physical experiment"));
        if (o.productionAvailable()) options.add(new Choice(Action.EXPLOIT,
                (0.2+0.65*o.competence())*(0.5+0.5*o.colonyUrgency())
                        - 0.4*distress, "Perform productive work"));
        return options.stream().max(Comparator.comparingDouble(Choice::score)
                .thenComparingInt(c -> -c.action().ordinal())).orElseThrow();
    }
}
