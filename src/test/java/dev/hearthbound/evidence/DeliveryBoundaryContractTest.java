package dev.hearthbound.evidence;

import java.util.UUID;

public final class DeliveryBoundaryContractTest {
    private static void check(boolean condition) { if (!condition) throw new AssertionError(); }
    public static void main(String[] args) {
        UUID world=UUID.randomUUID(), job=UUID.randomUUID(), actor=UUID.randomUUID();
        var pickup=new PickupTransactionJournal.Intent(world,job,actor,"overworld|3,101,1","report",1,2);
        var cargo=new PickupTransactionJournal.View(pickup,PickupTransactionJournal.State.CARGO_RETURNED);
        var empty=new PickupTransactionJournal.View(pickup,PickupTransactionJournal.State.EXTRACTION_EMPTY);
        var unresolved=new PickupTransactionJournal.View(pickup,PickupTransactionJournal.State.UNRESOLVED);
        var delivery=new DeliveryBoundaryContract.Intent(world,job,actor,"overworld|10,101,2",3);
        check(DeliveryBoundaryContract.admit(cargo,delivery,true,false)
            == DeliveryBoundaryContract.Decision.ADMIT_INSERTION_INTENT);
        check(DeliveryBoundaryContract.admit(null,delivery,true,false)
            == DeliveryBoundaryContract.Decision.DENY_NO_PICKUP);
        check(DeliveryBoundaryContract.admit(empty,delivery,true,false)
            == DeliveryBoundaryContract.Decision.DENY_NOT_EXTRACTED);
        check(DeliveryBoundaryContract.admit(unresolved,delivery,true,false)
            == DeliveryBoundaryContract.Decision.DENY_NOT_EXTRACTED);
        check(DeliveryBoundaryContract.admit(cargo,delivery,true,true)
            == DeliveryBoundaryContract.Decision.DENY_PREVIOUS_INSERTION);
        check(DeliveryBoundaryContract.admit(cargo,delivery,false,false)
            == DeliveryBoundaryContract.Decision.DENY_JOURNAL_UNAVAILABLE);
        check(DeliveryBoundaryContract.admit(cargo,
            new DeliveryBoundaryContract.Intent(world,UUID.randomUUID(),actor,"other",3),
            true,false)==DeliveryBoundaryContract.Decision.DENY_MISMATCH);
        check(DeliveryBoundaryContract.admit(cargo,
            new DeliveryBoundaryContract.Intent(world,job,UUID.randomUUID(),"other",3),
            true,false)==DeliveryBoundaryContract.Decision.DENY_MISMATCH);
        for(var decision:DeliveryBoundaryContract.Decision.values())
            check(!DeliveryBoundaryContract.authorizesAutomaticRetry(decision));
        System.out.println("DeliveryBoundaryContractTest passed");
    }
}
