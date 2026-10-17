package dev.hearthbound.research;

/**
 * Pure decision-boundary logic. Sampling at every entity tick would cause
 * oscillating jobs; active work commits until completion or interruption.
 */
public final class CitizenDecisionCadence {
    public enum WorkState { IDLE, TRAVELING, STUDYING, HAULING, INTERRUPTED, COMPLETED }
    public record Snapshot(boolean enabled, int priority, boolean knowsLesson,
                           boolean hauling, WorkState studyState,
                           long tick, long retryAfter) {}
    private CitizenDecisionCadence() {}

    public static boolean shouldConsider(Snapshot s) {
        if (s == null || s.studyState() == null) throw new IllegalArgumentException("missing snapshot");
        if (!s.enabled() || s.priority() <= 0 || s.knowsLesson() || s.hauling()
                || s.tick() < s.retryAfter()) return false;
        return switch (s.studyState()) {
            case IDLE, COMPLETED, INTERRUPTED -> true;
            case TRAVELING, STUDYING, HAULING -> false;
        };
    }
}
