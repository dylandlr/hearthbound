package dev.hearthbound.research;
import java.util.UUID;
public final class ScriptedCitizenWorkLoopTest {
    public static void main(String[] args) {
        var start = new ScriptedMillingExecutor.State(UUID.randomUUID(), UUID.randomUUID(),
                ScriptedMillingExecutor.Phase.UNASSIGNED);
        var supply = ScriptedCitizenWorkLoop.tick(start,
                new ScriptedCitizenWorkLoop.Snapshot(true,true,false,true,true,false,false,false));
        if (supply.action()!=ScriptedCitizenWorkLoop.Action.SUPPLY_WHEAT)
            throw new AssertionError("Must supply wheat before powering machine");
        var ready = ScriptedCitizenWorkLoop.tick(start,
                new ScriptedCitizenWorkLoop.Snapshot(true,false,true,true,true,false,false,false));
        if (ready.action()!=ScriptedCitizenWorkLoop.Action.ACTIVATE_POWER)
            throw new AssertionError("Must authorize power after loading wheat");
        var processing = ScriptedMillingExecutor.powered(ready.state());
        if (ScriptedCitizenWorkLoop.tick(processing,
                new ScriptedCitizenWorkLoop.Snapshot(true,false,false,true,true,false,false,false)).action()
                !=ScriptedCitizenWorkLoop.Action.OBSERVE)
            throw new AssertionError("Must wait for observed output");
        if (ScriptedCitizenWorkLoop.tick(processing,
                new ScriptedCitizenWorkLoop.Snapshot(true,false,false,true,true,false,false,true)).action()
                !=ScriptedCitizenWorkLoop.Action.REPORT_COMPLETION)
            throw new AssertionError("Must report completion after output");
        if (ScriptedCitizenWorkLoop.tick(start,
                new ScriptedCitizenWorkLoop.Snapshot(false,true,true,true,true,false,false,false)).action()
                !=ScriptedCitizenWorkLoop.Action.ABORT)
            throw new AssertionError("Unassigned work must abort");
        if (ScriptedCitizenWorkLoop.tick(start,
                new ScriptedCitizenWorkLoop.Snapshot(true,false,false,true,true,false,false,false)).action()
                !=ScriptedCitizenWorkLoop.Action.NONE)
            throw new AssertionError("Missing wheat must wait");
        System.out.println("ScriptedCitizenWorkLoop: 6 checks passed");
    }
}
