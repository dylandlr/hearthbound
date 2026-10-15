package dev.hearthbound.policy;

import java.util.List;
import static dev.hearthbound.policy.ColonyPolicy.Action;

/** Dependency-free smoke test: javac --release 17 + java, no Minecraft runtime required. */
public final class FirstMillRulesPolicySmokeTest {
    private static final FirstMillRulesPolicy POLICY = new FirstMillRulesPolicy();

    private static ColonyPolicy.Observation state(long version, int input, int heldWheat,
            int heldFlour, boolean blocked, boolean powered, boolean trained, Action... allowed) {
        return new ColonyPolicy.Observation(1, version, input, heldWheat, heldFlour,
                blocked ? 0 : 8, powered, blocked, trained, List.of(allowed));
    }

    private static void expect(Action expected, ColonyPolicy.Observation state) {
        ColonyPolicy.Decision decision = POLICY.decide(state);
        if (!ColonyPolicy.isValid(state, decision) || decision.action() != expected)
            throw new AssertionError("Expected " + expected + " but got " + decision);
    }

    public static void main(String[] args) {
        expect(Action.RESTOCK_WHEAT, state(1, 8, 0, 0, false, true, true,
                Action.RESTOCK_WHEAT, Action.WAIT));
        expect(Action.MILL_WHEAT, state(2, 0, 4, 0, false, true, true,
                Action.MILL_WHEAT, Action.WAIT));
        expect(Action.DELIVER_FLOUR, state(3, 0, 0, 2, false, true, true,
                Action.DELIVER_FLOUR, Action.WAIT));
        expect(Action.CLEAR_BLOCKAGE, state(4, 0, 0, 0, true, true, true,
                Action.CLEAR_BLOCKAGE, Action.WAIT));
        expect(Action.WAIT, state(5, 0, 4, 0, false, false, true, Action.WAIT));
        expect(Action.WAIT, state(6, 8, 0, 0, false, true, false, Action.WAIT));
        ColonyPolicy.Observation stale = state(7, 0, 0, 0, false, true, true, Action.WAIT);
        if (ColonyPolicy.isValid(stale, new ColonyPolicy.Decision(Action.WAIT, 6, "stale")))
            throw new AssertionError("Stale decision accepted");
        if (ColonyPolicy.isValid(stale, new ColonyPolicy.Decision(Action.MILL_WHEAT, 7, "not allowed")))
            throw new AssertionError("Unauthorized action accepted");
        System.out.println("PASS: 8 First Mill policy scenarios");
    }
}
