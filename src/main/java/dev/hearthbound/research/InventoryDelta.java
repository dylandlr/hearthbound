package dev.hearthbound.research;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/** Pure Java, fail-closed comparison of inventory snapshots; NOT a receipt. */
public final class InventoryDelta {
    public record Stack(String itemId, int count) {
        public Stack {
            Objects.requireNonNull(itemId, "itemId");
            if (itemId.isBlank() || count <= 0) throw new IllegalArgumentException("Invalid stack");
        }
    }
    public enum Quality { POSITIVE_DELTAS, NONE_OBSERVED, AMBIGUOUS }
    public record Result(Quality quality, List<Stack> increased) {
        public Result { increased = List.copyOf(increased); }
    }
    private InventoryDelta() {}

    public static Result compare(List<Stack> before, List<Stack> after) {
        Objects.requireNonNull(before); Objects.requireNonNull(after);
        if (before.size() != after.size()) throw new IllegalArgumentException("Slot count changed");
        List<Stack> increases = new ArrayList<>();
        boolean ambiguous = false;
        for (int i = 0; i < before.size(); i++) {
            Stack old = before.get(i), now = after.get(i);
            if (old == null && now == null) continue;
            if (old == null) { increases.add(now); continue; }
            if (now == null) { ambiguous = true; continue; }
            if (!old.itemId().equals(now.itemId())) { ambiguous = true; continue; }
            int change = now.count() - old.count();
            if (change > 0) increases.add(new Stack(now.itemId(), change));
            if (change < 0) ambiguous = true;
        }
        return new Result(ambiguous ? Quality.AMBIGUOUS :
                increases.isEmpty() ? Quality.NONE_OBSERVED : Quality.POSITIVE_DELTAS, increases);
    }
}
