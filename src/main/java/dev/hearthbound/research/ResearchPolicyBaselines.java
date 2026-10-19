package dev.hearthbound.research;

import java.util.Objects;

/**
 * Versioned, deterministic experiment-selection baselines.
 * The same partial observation is supplied to both policies; neither
 * accesses Minecraft world state, a hidden recipe list or global knowledge.
 */
public final class ResearchPolicyBaselines {
    public enum Mode { SCRIPTED, PERSONALITY }
    public record Decision(Mode mode, ExperimentSelectionPolicy.Choice choice) {}
    private static final ExperimentSelectionPolicy SELECTOR = new ExperimentSelectionPolicy();
    private ResearchPolicyBaselines() {}

    public static Decision choose(Mode mode, ExperimentSelectionPolicy.Observation observation) {
        Objects.requireNonNull(mode);
        Objects.requireNonNull(observation);
        // SCRIPTED uses a fixed curiosity coefficient across all citizens,
        // preserving other observed constraints. PERSONALITY uses the
        // citizen's genuine individual exploration instinct.
        var input = mode == Mode.SCRIPTED
                ? new ExperimentSelectionPolicy.Observation(
                    ExperimentSelectionPolicy.VERSION, .60,
                    observation.scarcity(), observation.fatigue(), observation.localCandidates())
                : observation;
        return new Decision(mode, SELECTOR.select(input));
    }
}
