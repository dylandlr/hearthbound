package dev.hearthbound.evidence;

/**
 * Deterministic reference planner for next observation contract.
 * Unlike the five-input imitation MLP this planner distinguishes lack of
 * evidence from a confirmed source shortage. This is NOT a trained model.
 */
public final class SourceAwareMillPlanner {
    private SourceAwareMillPlanner() {}
    public enum Availability { UNKNOWN, EMPTY, AVAILABLE }
    public enum Intent {
        INSPECT_SOURCE, WAIT_FOR_SUPPLY, REQUEST_WHEAT_HAUL,
        INSPECT_UNPOWERED, WAIT_FOR_PROCESSING, COLLECT_OUTPUT
    }
    public record Observation(boolean powered, boolean wheatPresent,
                              boolean flourPresent, boolean blocked,
                              Availability source, boolean taskActive) {
        public Observation {
            if (source==null) throw new IllegalArgumentException("missing source knowledge");
        }
    }
    public static Intent decide(Observation o) {
        if (o==null) throw new IllegalArgumentException("missing observation");
        if (!o.powered()) return Intent.INSPECT_UNPOWERED;
        if (o.flourPresent() || o.blocked()) return Intent.COLLECT_OUTPUT;
        if (o.wheatPresent() || o.taskActive()) return Intent.WAIT_FOR_PROCESSING;
        return switch(o.source()) {
            case UNKNOWN -> Intent.INSPECT_SOURCE;
            case EMPTY -> Intent.WAIT_FOR_SUPPLY;
            case AVAILABLE -> Intent.REQUEST_WHEAT_HAUL;
        };
    }
    /** Explicit no-dispatch contract. Execution requires separate live task checks. */
    public static boolean dispatchCandidate(Intent intent) {
        return intent == Intent.REQUEST_WHEAT_HAUL;
    }
}
