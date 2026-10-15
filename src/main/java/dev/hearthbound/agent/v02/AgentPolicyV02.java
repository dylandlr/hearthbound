package dev.hearthbound.agent.v02;

@FunctionalInterface
public interface AgentPolicyV02 {
    HierarchicalTask decide(MillObservation observation);
}
