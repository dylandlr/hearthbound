package dev.hearthbound.evidence;

import java.util.List;

/**
 * Stable v2 candidate tensor for training future policies. This class neither
 * runs the frozen 5-feature MLP nor executes any Minecraft task.
 *
 * Unknown source resources and stale known observations are not encoded as
 * empty inventories; consumers must honor one-hot source flags and staleness.
 */
public final class MillObservationV2 {
    public static final String SCHEMA = "hearthbound.mill-observation.v2";
    public static final int WIDTH = 10;
    public static final long STALE_AFTER_TICKS = 100L;
    public static final List<String> FEATURES = List.of(
        "powered", "mill_wheat_present", "mill_flour_present", "mill_blocked",
        "verified_experience_norm", "source_unknown", "source_empty",
        "source_available", "task_active", "source_stale"
    );
    public enum SourceState { UNKNOWN, EMPTY, AVAILABLE }

    /** Source sensor is observed at a tick no later than the decision tick. */
    public record Snapshot(
        boolean powered, boolean millWheat, boolean millFlour, boolean blocked,
        long verifiedExperience, SourceState source, boolean taskActive,
        long sourceObservationTick, long decisionTick) {
        public Snapshot {
            if (verifiedExperience < 0) throw new IllegalArgumentException("Negative experience");
            if (source == null) throw new IllegalArgumentException("Missing source state");
            if (decisionTick < 0 || sourceObservationTick < 0 || sourceObservationTick > decisionTick)
                throw new IllegalArgumentException("Impossible observation timestamps");
        }
        public boolean sourceStale() {
            return source != SourceState.UNKNOWN
                && decisionTick - sourceObservationTick > STALE_AFTER_TICKS;
        }
        public SourceState effectiveSource() {
            return sourceStale() ? SourceState.UNKNOWN : source;
        }
    }

    private MillObservationV2() {}

    public static double[] encode(Snapshot observation) {
        if (observation == null) throw new IllegalArgumentException("Missing observation");
        SourceState effective = observation.effectiveSource();
        double[] tensor = {
            observation.powered() ? 1.0 : 0.0,
            observation.millWheat() ? 1.0 : 0.0,
            observation.millFlour() ? 1.0 : 0.0,
            observation.blocked() ? 1.0 : 0.0,
            Math.min(10L, observation.verifiedExperience()) / 10.0,
            effective == SourceState.UNKNOWN ? 1.0 : 0.0,
            effective == SourceState.EMPTY ? 1.0 : 0.0,
            effective == SourceState.AVAILABLE ? 1.0 : 0.0,
            observation.taskActive() ? 1.0 : 0.0,
            observation.sourceStale() ? 1.0 : 0.0
        };
        if (tensor.length != WIDTH) throw new IllegalStateException("Schema width changed");
        return tensor;
    }

    /** No game actions, no trained model and no semantic upgrade of v1. */
    public static String featureCsv() { return String.join(",", FEATURES); }
}
