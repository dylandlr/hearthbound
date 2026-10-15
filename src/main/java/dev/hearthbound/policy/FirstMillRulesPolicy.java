package dev.hearthbound.policy;

import java.util.List;
import static dev.hearthbound.policy.ColonyPolicy.Action;

/** Deterministic baseline; selects a validated intention, never edits Minecraft state. */
public final class FirstMillRulesPolicy implements ColonyPolicy {
    @Override public String id() { return "rules:first-mill:v2"; }

    @Override public Decision decide(Observation state) {
        List<Action> allowed = state.availableActions();
        Action choice;
        String why;
        if (state.heldFlour() > 0 && allowed.contains(Action.DELIVER_FLOUR)) {
            choice = Action.DELIVER_FLOUR; why = "Deliver held cargo before starting more work";
        } else if (state.outputBlocked() && allowed.contains(Action.CLEAR_BLOCKAGE)) {
            choice = Action.CLEAR_BLOCKAGE; why = "Output destination blocked";
        } else if (state.heldWheat() > 0 && state.operatorTrained() && state.millPowered()
                && allowed.contains(Action.MILL_WHEAT)) {
            choice = Action.MILL_WHEAT; why = "Process already reserved wheat";
        } else if (state.inputWheat() > 0 && state.operatorTrained()
                && allowed.contains(Action.RESTOCK_WHEAT)) {
            choice = Action.RESTOCK_WHEAT; why = "Restock workshop input";
        } else {
            choice = Action.WAIT; why = "No safe productive action";
        }
        if (!allowed.contains(choice)) {
            // An empty allowed list represents a scheduling failure, not permission to act.
            throw new IllegalStateException("No safe action: WAIT absent from authorized actions");
        }
        return new Decision(choice, state.worldVersion(), why);
    }
}
