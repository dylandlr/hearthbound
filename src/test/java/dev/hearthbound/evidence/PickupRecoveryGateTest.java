package dev.hearthbound.evidence;

import java.util.UUID;

/** No Forge dependencies: restart classification must never authorize action. */
public final class PickupRecoveryGateTest {
    static void check(boolean good) { if (!good) throw new AssertionError(); }
    public static void main(String[] args) {
        UUID world = UUID.randomUUID(), actor = UUID.randomUUID(), job = UUID.randomUUID();
        var intent = new PickupTransactionJournal.Intent(
            world, job, actor, "minecraft:overworld|1,64,1", "report", 1, 2);
        var empty = new PickupTransactionJournal.View(
            intent, PickupTransactionJournal.State.EXTRACTION_EMPTY);
        var cargo = new PickupTransactionJournal.View(
            intent, PickupTransactionJournal.State.CARGO_RETURNED);
        var unresolved = new PickupTransactionJournal.View(
            intent, PickupTransactionJournal.State.UNRESOLVED);
        check(PickupRecoveryGate.classify(world, actor, job, null, true)
            == PickupRecoveryGate.Decision.PAUSE_NO_INTENT);
        check(PickupRecoveryGate.classify(world, actor, job, unresolved, true)
            == PickupRecoveryGate.Decision.QUARANTINE_UNRESOLVED);
        check(PickupRecoveryGate.classify(world, actor, job, empty, true)
            == PickupRecoveryGate.Decision.PAUSE_EMPTY_OUTCOME);
        check(PickupRecoveryGate.classify(world, actor, job, cargo, true)
            == PickupRecoveryGate.Decision.QUARANTINE_CARGO_OUTCOME);
        check(PickupRecoveryGate.classify(world, actor, job, empty, false)
            == PickupRecoveryGate.Decision.QUARANTINE_JOURNAL_UNAVAILABLE);
        check(PickupRecoveryGate.classify(UUID.randomUUID(), actor, job, empty, true)
            == PickupRecoveryGate.Decision.QUARANTINE_IDENTITY_MISMATCH);
        check(PickupRecoveryGate.classify(world, UUID.randomUUID(), job, cargo, true)
            == PickupRecoveryGate.Decision.QUARANTINE_IDENTITY_MISMATCH);
        check(PickupRecoveryGate.classify(world, actor, UUID.randomUUID(), empty, true)
            == PickupRecoveryGate.Decision.QUARANTINE_IDENTITY_MISMATCH);
        for (PickupRecoveryGate.Decision decision : PickupRecoveryGate.Decision.values()) {
            boolean safe = PickupRecoveryGate.permitsNoCargoCancellation(decision);
            check(safe == (decision == PickupRecoveryGate.Decision.PAUSE_NO_INTENT
                || decision == PickupRecoveryGate.Decision.PAUSE_EMPTY_OUTCOME));
        }
        // Absence of saved cargo must not erase a forced positive outcome.
        check(!PickupRecoveryGate.permitsNoCargoCancellation(
            PickupRecoveryGate.classify(world, actor, job, cargo, true)));
        check(!PickupRecoveryGate.permitsNoCargoCancellation(
            PickupRecoveryGate.classify(world, actor, job, unresolved, true)));
        check(!PickupRecoveryGate.permitsNoCargoCancellation(
            PickupRecoveryGate.classify(world, actor, job, null, false)));
        System.out.println("PickupRecoveryGateTest passed");
    }
}
