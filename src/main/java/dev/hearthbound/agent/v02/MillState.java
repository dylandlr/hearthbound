package dev.hearthbound.agent.v02;

public record MillState(
        int sourceWheat,
        int millWheat,
        int millFlour,
        int storeFlour,
        int cargoFlour,
        int flourTarget,
        HierarchicalTask currentTask,
        boolean lastActionFailed,
        long step) {

    public MillState {
        if (sourceWheat < 0 || millWheat < 0 || millFlour < 0 || storeFlour < 0
                || cargoFlour < 0 || flourTarget < 0 || step < 0)
            throw new IllegalArgumentException("State quantities cannot be negative");
        if (currentTask == null) throw new IllegalArgumentException("currentTask");
    }

    public static MillState homestead(int wheat, int flourTarget) {
        return new MillState(wheat, 0, 0, 0, 0, flourTarget,
                HierarchicalTask.WAIT, false, 0);
    }

    public int conservedUnits() {
        return sourceWheat + millWheat + millFlour + storeFlour + cargoFlour;
    }

    public boolean targetReached() {
        return storeFlour >= flourTarget;
    }
}
