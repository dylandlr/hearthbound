package dev.hearthbound.research;

import java.util.List;
import dev.hearthbound.research.InventoryDelta.*;

public final class InventoryDeltaTest {
    private static int checks;
    private static void ok(boolean value) { if (!value) throw new AssertionError(); checks++; }
    private static void rejects(Runnable call) {
        try { call.run(); throw new AssertionError("Expected rejection"); }
        catch (IllegalArgumentException expected) { checks++; }
    }
    public static void main(String[] args) {
        Stack wheat = new Stack("minecraft:wheat",2);
        Stack flour = new Stack("create:wheat_flour",1);
        ok(InventoryDelta.compare(List.of(),List.of()).quality()==Quality.NONE_OBSERVED);
        ok(InventoryDelta.compare(java.util.Arrays.asList((Stack)null),
                java.util.Arrays.asList(flour)).quality()==Quality.POSITIVE_DELTAS);
        ok(InventoryDelta.compare(List.of(flour),List.of(new Stack("create:wheat_flour",3))).increased()
                .equals(List.of(new Stack("create:wheat_flour",2))));
        ok(InventoryDelta.compare(List.of(wheat),List.of(new Stack("minecraft:wheat",1))).quality()==Quality.AMBIGUOUS);
        ok(InventoryDelta.compare(List.of(wheat),List.of(flour)).quality()==Quality.AMBIGUOUS);
        ok(InventoryDelta.compare(List.of(flour),java.util.Arrays.asList((Stack)null)).quality()==Quality.AMBIGUOUS);
        ok(InventoryDelta.compare(List.of(flour,wheat),
                List.of(new Stack("create:wheat_flour",3),new Stack("minecraft:wheat",1))).quality()==Quality.AMBIGUOUS);
        rejects(()->InventoryDelta.compare(List.of(flour),List.of()));
        rejects(()->new Stack("",1));
        rejects(()->new Stack("minecraft:wheat",0));
        System.out.println("InventoryDelta: "+checks+" checks passed");
    }
}
