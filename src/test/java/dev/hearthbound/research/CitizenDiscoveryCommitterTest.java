package dev.hearthbound.research;

import java.nio.file.Files;
import java.util.UUID;

public final class CitizenDiscoveryCommitterTest {
    public static void main(String[] args) throws Exception {
        var directory = Files.createTempDirectory("hearthbound-citizen-credit-");
        var citizen = UUID.randomUUID();
        var operation = UUID.randomUUID();
        var assignment = new CitizenDiscoveryGate.Assignment(operation, citizen, "world",
                "minecraft:overworld", "1,-59,1", "create:milling/wheat", true);
        var observed = new CitizenDiscoveryGate.Observation(operation, "world",
                "minecraft:overworld", "1,-59,1", "create:milling/wheat",
                "create:milling/wheat", 1, true, true);
        var writer = new CitizenDiscoveryCommitter(directory);
        if (!writer.commit(assignment, observed, "stable-real-receipt-v1").newlyCredited())
            throw new AssertionError("First credit absent");
        if (writer.commit(assignment, observed, "stable-real-receipt-v1").newlyCredited())
            throw new AssertionError("Duplicate credit");
        var reloaded = new CitizenDiscoveryCommitter(directory);
        if (reloaded.balance(citizen) != 1
                || reloaded.commit(assignment, observed, "stable-real-receipt-v1").newlyCredited())
            throw new AssertionError("Credit failed restart/idempotence");
        boolean conflict = false;
        try { reloaded.commit(assignment, observed, "conflicting-receipt"); }
        catch (java.io.IOException expected) { conflict = true; }
        if (!conflict) throw new AssertionError("Conflicting retry accepted");
        boolean rejected = false;
        try { reloaded.commit(assignment, new CitizenDiscoveryGate.Observation(operation,
                "world", "minecraft:overworld", "1,-59,1", "create:milling/wheat",
                "create:milling/wheat", 1, false, true), "forbidden-receipt"); }
        catch (IllegalArgumentException expected) { rejected = true; }
        if (!rejected || reloaded.balance(citizen) != 1)
            throw new AssertionError("Rejected evidence changed credit");
        System.out.println("CitizenDiscoveryCommitter: 5 checks passed");
    }
}
