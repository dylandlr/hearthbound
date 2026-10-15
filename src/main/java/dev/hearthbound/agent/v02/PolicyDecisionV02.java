package dev.hearthbound.agent.v02;

public record PolicyDecisionV02(
        String observationVersion,
        long expectedWorldVersion,
        HierarchicalTask action) {

    public static final String VERSION = "hearthbound.agent.decision.v0.2";

    public PolicyDecisionV02 {
        if (!MillObservation.VERSION.equals(observationVersion))
            throw new IllegalArgumentException("Unsupported observation version");
        if (expectedWorldVersion < 0 || action == null)
            throw new IllegalArgumentException("Invalid policy decision");
    }

    public static PolicyDecisionV02 from(MillObservation observation, AgentPolicyV02 policy) {
        if (observation == null || policy == null) throw new IllegalArgumentException("Missing decision input");
        return new PolicyDecisionV02(MillObservation.VERSION, observation.step(), policy.decide(observation));
    }
}
