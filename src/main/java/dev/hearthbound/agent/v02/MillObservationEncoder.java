package dev.hearthbound.agent.v02;

import java.util.List;

public final class MillObservationEncoder {
    public static final String VERSION = "hearthbound.agent.vector.v0.2";
    public static final List<String> FEATURE_NAMES = List.of(
            "bias", "cargo_flour", "source_visible", "source_wheat",
            "mill_visible", "mill_wheat", "mill_flour", "store_visible",
            "store_flour", "target_remaining", "source_available",
            "mill_input_available", "mill_output_available", "cargo_available",
            "at_wait", "task_wait", "task_supply", "task_collect",
            "task_return", "last_action_failed");

    private MillObservationEncoder() {}

    public static float[] encode(MillObservation o) {
        float source = o.sourceVisible() ? norm(o.sourceWheat()) : 0f;
        float millWheat = o.millVisible() ? norm(o.millWheat()) : 0f;
        float millFlour = o.millVisible() ? norm(o.millFlour()) : 0f;
        float store = o.storeVisible() ? norm(o.storeFlour()) : 0f;
        int knownStore = o.storeVisible() ? o.storeFlour() : 0;
        return new float[] {
                1f, norm(o.cargoFlour()), bit(o.sourceVisible()), source,
                bit(o.millVisible()), millWheat, millFlour, bit(o.storeVisible()),
                store, norm(Math.max(0, o.flourTarget() - knownStore)),
                bit(o.allows(HierarchicalTask.SUPPLY_MILL)),
                bit(o.millVisible() && o.millWheat() > 0),
                bit(o.allows(HierarchicalTask.COLLECT_FLOUR)),
                bit(o.cargoFlour() > 0), bit(o.currentTask() == HierarchicalTask.WAIT),
                bit(o.currentTask() == HierarchicalTask.WAIT),
                bit(o.currentTask() == HierarchicalTask.SUPPLY_MILL),
                bit(o.currentTask() == HierarchicalTask.COLLECT_FLOUR),
                bit(o.currentTask() == HierarchicalTask.RETURN_TO_WAIT),
                bit(o.lastActionFailed())
        };
    }

    private static float norm(int value) {
        return Math.min(1f, value / 64f);
    }

    private static float bit(boolean value) {
        return value ? 1f : 0f;
    }
}
