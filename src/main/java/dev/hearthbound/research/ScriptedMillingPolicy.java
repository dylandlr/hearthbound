package dev.hearthbound.research;

/**
 * Deterministic control policy used as the first learning baseline.
 * It sees an explicitly bounded snapshot, not arbitrary server state.
 * Decisions have no side-effects; the server executes authorized actions.
 */
public final class ScriptedMillingPolicy {
    public enum Decision { PREPARE_MILLING, WAIT, ABORT }
    public record Observation(boolean assigned, boolean wheatAvailable,
                              boolean millstoneAvailable, boolean motorAvailable,
                              boolean dangerous, boolean operationAlreadyCredited) {}
    public static Decision choose(Observation observation) {
        if (observation == null || !observation.assigned()
                || observation.dangerous() || observation.operationAlreadyCredited())
            return Decision.ABORT;
        if (!observation.wheatAvailable() || !observation.millstoneAvailable()
                || !observation.motorAvailable())
            return Decision.WAIT;
        return Decision.PREPARE_MILLING;
    }
    private ScriptedMillingPolicy() {}
}
