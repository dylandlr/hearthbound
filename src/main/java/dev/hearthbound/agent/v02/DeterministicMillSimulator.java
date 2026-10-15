package dev.hearthbound.agent.v02;

import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

public final class DeterministicMillSimulator {
    public static final String VERSION = "hearthbound.agent.simulator.v0.2";

    public record Transition(MillState before, HierarchicalTask action,
                             MillState after, RewardFrame reward, boolean accepted) {}

    private final long seed;
    private MillState state;

    public DeterministicMillSimulator(MillState initial, long seed) {
        state = initial;
        this.seed = seed;
    }

    public long seed() { return seed; }
    public MillState state() { return state; }

    public MillObservation observe() {
        HierarchicalTask task = state.currentTask();
        boolean sourceVisible = task == HierarchicalTask.SUPPLY_MILL;
        boolean millVisible = task == HierarchicalTask.SUPPLY_MILL
                || task == HierarchicalTask.COLLECT_FLOUR;
        boolean storeVisible = task == HierarchicalTask.WAIT
                || task == HierarchicalTask.RETURN_TO_WAIT;
        return new MillObservation(sourceVisible, sourceVisible ? state.sourceWheat() : 0,
                millVisible, millVisible ? state.millWheat() : 0,
                millVisible ? state.millFlour() : 0,
                storeVisible, storeVisible ? state.storeFlour() : 0,
                state.cargoFlour(), state.flourTarget(), task,
                state.lastActionFailed(), actionMask(), state.step());
    }

    public Set<HierarchicalTask> actionMask() {
        EnumSet<HierarchicalTask> mask = EnumSet.of(HierarchicalTask.WAIT);
        if (state.sourceWheat() > 0 && state.cargoFlour() == 0)
            mask.add(HierarchicalTask.SUPPLY_MILL);
        if (state.millFlour() > 0 && state.cargoFlour() == 0)
            mask.add(HierarchicalTask.COLLECT_FLOUR);
        if (state.cargoFlour() > 0)
            mask.add(HierarchicalTask.RETURN_TO_WAIT);
        return mask;
    }

    public Transition step(HierarchicalTask action) {
        MillState before = state;
        if (action == null || !actionMask().contains(action)) {
            RewardFrame reward = new RewardFrame(Map.of("invalid_action", -0.25), Map.of());
            return new Transition(before, action, before, reward, false);
        }

        int source = before.sourceWheat();
        int input = before.millWheat();
        int output = before.millFlour();
        int store = before.storeFlour();
        int cargo = before.cargoFlour();
        Map<String, Double> personal = new LinkedHashMap<>();
        Map<String, Double> colony = new LinkedHashMap<>();

        switch (action) {
            case SUPPLY_MILL -> {
                source--;
                input++;
                personal.put("useful_supply", 0.02);
            }
            case COLLECT_FLOUR -> {
                output--;
                cargo++;
                personal.put("useful_collection", 0.02);
            }
            case RETURN_TO_WAIT -> {
                int delivered = cargo;
                cargo = 0;
                store += delivered;
                personal.put("completed_delivery", 0.03 * delivered);
                colony.put("flour_delivered", 1.0 * delivered);
                if (before.storeFlour() < before.flourTarget() && store >= before.flourTarget())
                    colony.put("target_reached", 2.0);
            }
            case WAIT -> personal.put("wait_cost", -0.001);
        }

        if (input > 0) {
            input--;
            output++;
        }

        MillState after = new MillState(source, input, output, store, cargo,
                before.flourTarget(), action, false, before.step() + 1);
        if (after.conservedUnits() != before.conservedUnits())
            throw new IllegalStateException("Inventory conservation violated");
        state = after;
        return new Transition(before, action, after,
                new RewardFrame(personal, colony), true);
    }
}
