package dev.hearthbound.research;
public final class ScriptedMillingPolicyTest {
    public static void main(String[] args) {
        var ready = new ScriptedMillingPolicy.Observation(true, true, true, true, false, false);
        if (ScriptedMillingPolicy.choose(ready) != ScriptedMillingPolicy.Decision.PREPARE_MILLING)
            throw new AssertionError("Ready task not selected");
        var empty = new ScriptedMillingPolicy.Observation(true, false, true, true, false, false);
        if (ScriptedMillingPolicy.choose(empty) != ScriptedMillingPolicy.Decision.WAIT)
            throw new AssertionError("Missing wheat should wait");
        var forbidden = new ScriptedMillingPolicy.Observation(false, true, true, true, false, false);
        if (ScriptedMillingPolicy.choose(forbidden) != ScriptedMillingPolicy.Decision.ABORT)
            throw new AssertionError("Unassigned task should abort");
        var danger = new ScriptedMillingPolicy.Observation(true, true, true, true, true, false);
        if (ScriptedMillingPolicy.choose(danger) != ScriptedMillingPolicy.Decision.ABORT)
            throw new AssertionError("Danger should abort");
        var duplicate = new ScriptedMillingPolicy.Observation(true, true, true, true, false, true);
        if (ScriptedMillingPolicy.choose(duplicate) != ScriptedMillingPolicy.Decision.ABORT)
            throw new AssertionError("Credited operation should abort");
        System.out.println("ScriptedMillingPolicy: 5 checks passed");
    }
}
