package dev.hearthbound.agent.v02;

import java.util.EnumSet;

public final class DecisionGateV02SmokeTest {
    private static void verify(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static MillObservation observation(long step, HierarchicalTask... allowed) {
        EnumSet<HierarchicalTask> mask = EnumSet.noneOf(HierarchicalTask.class);
        for (HierarchicalTask action : allowed) mask.add(action);
        return new MillObservation(true, 8, true, 0, 0, true, 0,
                0, 4, HierarchicalTask.WAIT, false, mask, step);
    }

    public static void main(String[] args) {
        MillObservation current = observation(50, HierarchicalTask.WAIT, HierarchicalTask.SUPPLY_MILL);
        PolicyDecisionV02 accepted = new PolicyDecisionV02(
                MillObservation.VERSION, 50, HierarchicalTask.SUPPLY_MILL);
        verify(DecisionGateV02.validate(current, accepted) == DecisionGateV02.Rejection.NONE,
                "valid decision rejected");

        PolicyDecisionV02 stale = new PolicyDecisionV02(
                MillObservation.VERSION, 49, HierarchicalTask.SUPPLY_MILL);
        verify(DecisionGateV02.validate(current, stale)
                == DecisionGateV02.Rejection.STALE_OBSERVATION, "stale decision accepted");

        PolicyDecisionV02 masked = new PolicyDecisionV02(
                MillObservation.VERSION, 50, HierarchicalTask.COLLECT_FLOUR);
        verify(DecisionGateV02.validate(current, masked)
                == DecisionGateV02.Rejection.ACTION_MASKED, "masked decision accepted");

        PolicyDecisionV02 scripted = PolicyDecisionV02.from(current, new ScriptedMillPolicyV02());
        verify(scripted.action() == HierarchicalTask.SUPPLY_MILL
                && scripted.expectedWorldVersion() == 50, "policy decision lost version");

        boolean wrongVersionRejected = false;
        try {
            new PolicyDecisionV02("v0.1", 50, HierarchicalTask.WAIT);
        } catch (IllegalArgumentException expected) {
            wrongVersionRejected = true;
        }
        verify(wrongVersionRejected, "wrong schema accepted");
        System.out.println("PASS: v0.2 stale/masked server decision gate");
    }
}
