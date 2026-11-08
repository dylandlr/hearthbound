package dev.hearthbound.evidence;

import java.util.UUID;

public final class PickupFailureContractTest {
    private static int checks;
    private static void ok(boolean v) {
        checks++;
        if (!v) throw new AssertionError("pickup failure contract assertion " + checks);
    }
    private static void bad(Runnable r) {
        boolean failed=false;
        try {r.run();} catch (IllegalArgumentException | NullPointerException valid) { failed=true; }
        ok(failed);
    }
    public static void main(String[] args) {
        UUID world=UUID.randomUUID(), job=UUID.randomUUID(),
            executor=UUID.randomUUID(), scout=UUID.randomUUID();
        String source="minecraft:overworld|3,101,1";
        String id=scout+"|"+source+"|1";
        var failure=new PickupFailureContract.Failure(
            world,job,executor,source,id,100,180,
            PickupFailureContract.OBSERVATION);
        var old=new PickupFailureContract.Report(source,id,90,95);
        ok(PickupFailureContract.disqualifies(failure,world,executor,old));
        ok(PickupFailureContract.matches(failure,world,job,executor,
            source,id,100,180));
        ok(!PickupFailureContract.matches(failure,world,UUID.randomUUID(),executor,
            source,id,100,180));
        ok(!PickupFailureContract.matches(failure,UUID.randomUUID(),job,executor,
            source,id,100,180));
        ok(!PickupFailureContract.matches(failure,world,job,scout,source,id,100,180));
        ok(!PickupFailureContract.matches(failure,world,job,executor,source,id,101,180));
        ok(!PickupFailureContract.matches(failure,world,job,executor,source,id,100,181));
        ok(!PickupFailureContract.matches(failure,world,job,executor,
            "minecraft:overworld|7,101,1",id,100,180));
        ok(!PickupFailureContract.disqualifies(failure,UUID.randomUUID(),executor,old));
        ok(!PickupFailureContract.disqualifies(failure,world,scout,old));
        ok(!PickupFailureContract.disqualifies(failure,world,executor,
            new PickupFailureContract.Report("minecraft:overworld|7,101,1",
                "different",100,101)));
        // Re-delivering the same report after failure does not launder it.
        ok(PickupFailureContract.disqualifies(failure,world,executor,
            new PickupFailureContract.Report(source,id,200,201)));
        // A distinct report from before the physical failure is still stale.
        ok(PickupFailureContract.disqualifies(failure,world,executor,
            new PickupFailureContract.Report(source,"another-sender",179,190)));
        // The ONLY permitted new report observes the source after failure.
        ok(!PickupFailureContract.disqualifies(failure,world,executor,
            new PickupFailureContract.Report(source,"revision-2",181,190)));
        ok(PickupFailureContract.disqualifies(failure,world,executor,
            new PickupFailureContract.Report(source,"revision-2",180,190)));
        ok(!PickupFailureContract.disqualifies(null,world,executor,old));
        ok(!PickupFailureContract.disqualifies(failure,null,executor,old));
        ok(!PickupFailureContract.disqualifies(failure,world,null,old));
        bad(()->new PickupFailureContract.Failure(world,job,executor,source,id,200,180,
            PickupFailureContract.OBSERVATION));
        bad(()->new PickupFailureContract.Failure(world,job,executor,source,id,100,180,
            "BLOCKED_NAVIGATION"));
        bad(()->new PickupFailureContract.Failure(world,job,executor,source,id,100,180,
            "EMPTY_CHEST_INFERRED_FROM_TIMEOUT"));
        bad(()->new PickupFailureContract.Failure(world,job,executor,source,"NONE",100,180,
            PickupFailureContract.OBSERVATION));
        bad(()->new PickupFailureContract.Failure(world,job,executor,"",id,100,180,
            PickupFailureContract.OBSERVATION));
        bad(()->new PickupFailureContract.Report(source,"old",200,190));
        bad(()->new PickupFailureContract.Report(source,"",100,101));
        ok(PickupFailureContract.SCHEMA.equals("hearthbound.pickup-failure.v1"));
        System.out.println("PickupFailureContractTest: "+checks+
            " passed (physical extraction only; no synthetic world or rewards)");
    }
}
