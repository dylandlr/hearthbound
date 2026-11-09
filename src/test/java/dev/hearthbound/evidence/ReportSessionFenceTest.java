package dev.hearthbound.evidence;

import java.util.UUID;

public final class ReportSessionFenceTest {
    private static int checks;
    private static void ok(boolean value) {
        checks++;
        if (!value) throw new AssertionError("session fence check " + checks);
    }
    public static void main(String[] args) {
        UUID world = UUID.randomUUID(), boot1 = UUID.randomUUID(), boot2 = UUID.randomUUID();
        var first = new ReportSessionFence(world, boot1);
        var restarted = new ReportSessionFence(world, boot2);
        ok(first.accepts(world, boot1, 90, 95, 100));
        ok(!restarted.accepts(world, boot1, 90, 95, 100));
        // A rolled-back clock, redelivery or future forged timestamp cannot renew a session.
        ok(!restarted.accepts(world, boot1, 90, 110, 110));
        ok(!restarted.accepts(world, boot1, 110, 110, 110));
        ok(!restarted.accepts(world, boot1, 90, 95, 80));
        ok(restarted.accepts(world, boot2, 90, 95, 100));
        ok(!first.accepts(UUID.randomUUID(), boot1, 90, 95, 100));
        ok(!first.accepts(null, boot1, 90, 95, 100));
        ok(!first.accepts(world, null, 90, 95, 100));
        ok(!first.accepts(world, boot1, -1, 95, 100));
        ok(!first.accepts(world, boot1, 96, 95, 100));
        ok(!first.accepts(world, boot1, 90, 101, 100));
        UUID actor = UUID.randomUUID();
        var miss = new PickupFailureContract.Failure(world, UUID.randomUUID(), actor,
            "minecraft:overworld|3,101,1", "original-report", 10, 20, PickupFailureContract.OBSERVATION);
        ok(PickupFailureContract.validInContext(miss, world, actor, 20));
        ok(!PickupFailureContract.validInContext(miss, UUID.randomUUID(), actor, 20));
        ok(!PickupFailureContract.validInContext(miss, world, UUID.randomUUID(), 20));
        ok(!PickupFailureContract.validInContext(miss, world, actor, 19));
        ok(!PickupFailureContract.validInContext(null, world, actor, 20));
        System.out.println("ReportSessionFenceTest: " + checks + " passed (no crash-durability claim)");
    }
}
