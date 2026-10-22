package dev.hearthbound.learning;

import dev.hearthbound.research.ExperimentSelectionPolicy;
import java.util.Arrays;
import java.util.List;

/**
 * Pure, fixed-width, partially-observed research policy features.
 * Inputs come from citizen-local ExperimentSelectionPolicy observations only.
 * No global recipe knowledge, other-citizen internals, or fabricated physiology.
 */
public final class ResearchObservationVector {
    public static final int VERSION = 1;
    public static final int WIDTH = 11;
    public static final List<String> FEATURE_NAMES = List.of(
            "curiosity", "scarcity", "fatigue", "candidate_present",
            "novelty", "material_cost", "material_visible", "machine_visible",
            "previously_falsified", "candidate_count_normalized", "eligible_count_normalized");

    private final double[] values;

    private ResearchObservationVector(double[] values) {
        if (values.length != WIDTH) throw new IllegalArgumentException("feature width");
        for (double value : values)
            if (!Double.isFinite(value) || value < 0 || value > 1)
                throw new IllegalArgumentException("features must be finite and normalized");
        this.values = values.clone();
    }

    /** Deterministic order prevents policy-input drift across seeds and JVM runs. */
    public static ResearchObservationVector from(ExperimentSelectionPolicy.Observation observation) {
        if (observation == null) throw new IllegalArgumentException("missing observation");
        var candidates = observation.localCandidates();
        // The observation is a limited local candidate list, not a world scan.
        var candidate = candidates.stream()
                .sorted(java.util.Comparator.comparing(ExperimentSelectionPolicy.Candidate::recipeId))
                .findFirst().orElse(null);
        long eligible = candidates.stream().filter(c ->
                c.materialVisible() && c.machineVisible() && !c.previouslyFalsified()).count();
        return new ResearchObservationVector(new double[]{
                observation.curiosity(), observation.scarcity(), observation.fatigue(),
                candidate == null ? 0 : 1,
                candidate == null ? 0 : candidate.novelty(),
                candidate == null ? 0 : candidate.materialCost(),
                candidate != null && candidate.materialVisible() ? 1 : 0,
                candidate != null && candidate.machineVisible() ? 1 : 0,
                candidate != null && candidate.previouslyFalsified() ? 1 : 0,
                Math.min(1, candidates.size() / 16.0),
                Math.min(1, eligible / 16.0)
        });
    }

    public int version() { return VERSION; }
    public double[] values() { return values.clone(); }
    public double value(int index) { return values[index]; }

    @Override public boolean equals(Object other) {
        return other instanceof ResearchObservationVector v && Arrays.equals(values, v.values);
    }
    @Override public int hashCode() { return Arrays.hashCode(values); }
}
