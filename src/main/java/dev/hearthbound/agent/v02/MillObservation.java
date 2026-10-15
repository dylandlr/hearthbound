package dev.hearthbound.agent.v02;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Set;

public record MillObservation(
        boolean sourceVisible,
        int sourceWheat,
        boolean millVisible,
        int millWheat,
        int millFlour,
        boolean storeVisible,
        int storeFlour,
        int cargoFlour,
        int flourTarget,
        HierarchicalTask currentTask,
        boolean lastActionFailed,
        Set<HierarchicalTask> actionMask,
        long step) {

    public static final String VERSION = "hearthbound.agent.observation.v0.2";

    public MillObservation {
        if (sourceWheat < 0 || millWheat < 0 || millFlour < 0 || storeFlour < 0
                || cargoFlour < 0 || flourTarget < 0 || step < 0)
            throw new IllegalArgumentException("Observation quantities cannot be negative");
        if (currentTask == null || actionMask == null) throw new IllegalArgumentException("null field");
        actionMask = Collections.unmodifiableSet(actionMask.isEmpty()
                ? EnumSet.noneOf(HierarchicalTask.class)
                : EnumSet.copyOf(actionMask));
    }

    public boolean allows(HierarchicalTask action) {
        return actionMask.contains(action);
    }
}
