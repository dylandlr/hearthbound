package dev.hearthbound.policy;

import java.util.List;

/** Versioned, bounded contract shared by scripted and learned policies. */
public interface ColonyPolicy {
    String id();

    Decision decide(Observation observation);

    enum Action { MILL_WHEAT, DELIVER_FLOUR, RESTOCK_WHEAT, CLEAR_BLOCKAGE, WAIT }

    record Observation(
            int schemaVersion, long worldVersion,
            int inputWheat, int heldWheat, int heldFlour,
            int outputFreeSlots, boolean millPowered,
            boolean outputBlocked, boolean operatorTrained,
            List<Action> availableActions) {
        public Observation {
            if (schemaVersion != 1) throw new IllegalArgumentException("Unsupported observation version");
            if (worldVersion < 0 || inputWheat < 0 || heldWheat < 0 || heldFlour < 0 || outputFreeSlots < 0)
                throw new IllegalArgumentException("Invalid inventory state");
            availableActions = List.copyOf(availableActions);
        }
    }

    record Decision(Action action, long expectedWorldVersion, String reason) {
        public Decision {
            if (action == null || reason == null) throw new IllegalArgumentException("Missing decision field");
        }
    }

    /** Reject unsafe, stale or hallucinated decisions before server-side execution. */
    static boolean isValid(Observation obs, Decision decision) {
        return decision != null
                && decision.expectedWorldVersion() == obs.worldVersion()
                && obs.availableActions().contains(decision.action());
    }
}
