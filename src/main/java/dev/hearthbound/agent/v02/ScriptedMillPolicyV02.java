package dev.hearthbound.agent.v02;

public final class ScriptedMillPolicyV02 implements AgentPolicyV02 {
    @Override
    public HierarchicalTask decide(MillObservation observation) {
        if (observation.allows(HierarchicalTask.RETURN_TO_WAIT))
            return HierarchicalTask.RETURN_TO_WAIT;
        if (observation.allows(HierarchicalTask.COLLECT_FLOUR))
            return HierarchicalTask.COLLECT_FLOUR;
        if (observation.allows(HierarchicalTask.SUPPLY_MILL))
            return HierarchicalTask.SUPPLY_MILL;
        return HierarchicalTask.WAIT;
    }
}
