package dev.hearthbound.policy;

import java.util.List;
import static dev.hearthbound.policy.ColonyPolicy.Action;

/** Checks rules never manufacture a forbidden WAIT action. */
public final class FirstMillPolicyBoundarySmokeTest {
    static ColonyPolicy.Observation state(List<Action> actions) {
        return new ColonyPolicy.Observation(1, 3, 0, 0, 0, 0, false,
                false, false, actions);
    }
    public static void main(String[] args) {
        FirstMillRulesPolicy policy = new FirstMillRulesPolicy();
        if (!ColonyPolicy.isValid(state(List.of(Action.WAIT)),
                policy.decide(state(List.of(Action.WAIT)))))
            throw new AssertionError("Authorized WAIT was rejected");
        for (List<Action> actions : List.of(List.<Action>of(),
                List.of(Action.MILL_WHEAT), List.of(Action.RESTOCK_WHEAT))) {
            boolean rejected = false;
            try { policy.decide(state(actions)); }
            catch (IllegalStateException ex) { rejected = true; }
            if (!rejected) throw new AssertionError("Allowed unauthorized choice: " + actions);
        }
        System.out.println("PASS: policy rejects 3 unsafe action sets");
    }
}
