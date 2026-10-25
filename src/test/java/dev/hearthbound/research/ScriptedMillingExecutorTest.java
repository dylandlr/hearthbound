package dev.hearthbound.research;
import java.util.UUID;
public final class ScriptedMillingExecutorTest {
    public static void main(String[] args) {
        UUID op = UUID.randomUUID(), citizen = UUID.randomUUID();
        var initial = new ScriptedMillingExecutor.State(op, citizen, ScriptedMillingExecutor.Phase.UNASSIGNED);
        var ready = new ScriptedMillingPolicy.Observation(true,true,true,true,false,false);
        var planned = ScriptedMillingExecutor.plan(initial,ready);
        if (!planned.authorizeMotorActivation() || planned.state().phase() != ScriptedMillingExecutor.Phase.READY_TO_POWER)
            throw new AssertionError("Ready task did not authorize power");
        var active = ScriptedMillingExecutor.powered(planned.state());
        if (ScriptedMillingExecutor.plan(active,ready).authorizeMotorActivation())
            throw new AssertionError("Powered task authorized a second activation");
        var eligible = new CitizenDiscoveryGate.Eligible(op,citizen,"create:milling/wheat");
        var completed = ScriptedMillingExecutor.complete(active,eligible);
        if (ScriptedMillingExecutor.plan(completed,ready).authorizeMotorActivation())
            throw new AssertionError("Completed task reactivated");
        boolean mismatch = false;
        try { ScriptedMillingExecutor.complete(active,
                new CitizenDiscoveryGate.Eligible(UUID.randomUUID(),citizen,"create:milling/wheat")); }
        catch (IllegalArgumentException expected) { mismatch=true; }
        if (!mismatch) throw new AssertionError("Foreign operation accepted");
        var waiting = new ScriptedMillingPolicy.Observation(true,false,true,true,false,false);
        if (ScriptedMillingExecutor.plan(initial,waiting).authorizeMotorActivation())
            throw new AssertionError("Missing inputs enabled motor");
        var unauthorized = new ScriptedMillingPolicy.Observation(false,true,true,true,false,false);
        if (ScriptedMillingExecutor.plan(initial,unauthorized).state().phase()!= ScriptedMillingExecutor.Phase.ABORTED)
            throw new AssertionError("Unauthorized task not aborted");
        System.out.println("ScriptedMillingExecutor: 6 checks passed");
    }
}
