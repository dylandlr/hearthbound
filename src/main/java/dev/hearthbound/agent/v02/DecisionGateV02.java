package dev.hearthbound.agent.v02;

public final class DecisionGateV02 {
    public enum Rejection { NONE, STALE_OBSERVATION, ACTION_MASKED }

    private DecisionGateV02() {}

    public static Rejection validate(MillObservation current, PolicyDecisionV02 decision) {
        if (current == null || decision == null) throw new IllegalArgumentException("Missing gate input");
        if (decision.expectedWorldVersion() != current.step()) return Rejection.STALE_OBSERVATION;
        if (!current.allows(decision.action())) return Rejection.ACTION_MASKED;
        return Rejection.NONE;
    }
}
