package dev.hearthbound.evidence;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;

/** Standalone Java 17 delivery journal recovery contract. */
public final class DeliveryJournalReplayTest {
    private static void check(boolean ok) { if(!ok) throw new AssertionError(); }
    @FunctionalInterface interface Checked { void call() throws Exception; }
    private static void denied(Checked action) throws Exception {
        try { action.call(); throw new AssertionError("unsafe operation allowed"); }
        catch (java.io.IOException expected) { }
    }
    private static PickupTransactionJournal.Intent pickup(UUID world, UUID job, UUID actor) {
        return new PickupTransactionJournal.Intent(
            world, job, actor, "minecraft:overworld|3,101,1", "report", 1, 2);
    }
    public static void main(String[] args) throws Exception {
        UUID world=UUID.randomUUID(), actor=UUID.randomUUID();
        UUID inserted=UUID.randomUUID(), interrupted=UUID.randomUUID(), empty=UUID.randomUUID();
        Path file=Files.createTempFile("hearthbound-delivery-journal", ".bin");
        var completeIntent=new DeliveryBoundaryContract.Intent(
            world,inserted,actor,"minecraft:overworld|10,101,2",3);
        var unresolvedIntent=new DeliveryBoundaryContract.Intent(
            world,interrupted,actor,"minecraft:overworld|10,101,2",4);
        try (var journal=new PickupTransactionJournal(file,world)) {
            journal.begin(pickup(world,inserted,actor));
            journal.finish(inserted,PickupTransactionJournal.State.CARGO_RETURNED);
            journal.beginDelivery(completeIntent);
            journal.finishDelivery(inserted);
            check(journal.inspectDelivery(inserted)
                == PickupTransactionJournal.DeliveryState.INSERTION_RETURNED);
            denied(()->journal.finishDelivery(inserted));
            denied(()->journal.beginDelivery(completeIntent));
            journal.begin(pickup(world,interrupted,actor));
            journal.finish(interrupted,PickupTransactionJournal.State.CARGO_RETURNED);
            journal.beginDelivery(unresolvedIntent);
            journal.begin(pickup(world,empty,actor));
            journal.finish(empty,PickupTransactionJournal.State.EXTRACTION_EMPTY);
            denied(()->journal.beginDelivery(new DeliveryBoundaryContract.Intent(
                world,empty,actor,"minecraft:overworld|10,101,2",6)));
        }
        try (var reopened=new PickupTransactionJournal(file,world)) {
            check(reopened.inspectDelivery(inserted)
                == PickupTransactionJournal.DeliveryState.INSERTION_RETURNED);
            check(reopened.inspectDelivery(interrupted)
                == PickupTransactionJournal.DeliveryState.INSERTION_UNRESOLVED);
            check(reopened.inspectDelivery(empty)
                == PickupTransactionJournal.DeliveryState.NOT_STARTED);
            denied(()->reopened.beginDelivery(unresolvedIntent));
            // An insertion RETURNED receipt is still not a saved-inventory
            // proof and must not authorize a second pickup from that source.
            check(PickupSourceAdmission.classify(reopened.snapshot(),
                pickup(world,UUID.randomUUID(),actor))
                == PickupSourceAdmission.Decision.DENY_UNRECONCILED_CARGO);
        }
        System.out.println("DeliveryJournalReplayTest passed");
    }
}
