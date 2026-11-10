package dev.hearthbound.evidence;

import java.util.List;
import java.util.UUID;

public final class PickupSourceAdmissionTest {
    private static void check(boolean x) { if (!x) throw new AssertionError(); }
    private static PickupTransactionJournal.Intent intent(UUID world, UUID job, String source) {
        return new PickupTransactionJournal.Intent(
            world, job, UUID.randomUUID(), source, "report", 1, 2);
    }
    public static void main(String[] args) {
        UUID world=UUID.randomUUID(), oldJob=UUID.randomUUID();
        var existing=intent(world,oldJob,"minecraft:overworld|3,101,1");
        var sameSource=intent(world,UUID.randomUUID(),"minecraft:overworld|3,101,1");
        var otherSource=intent(world,UUID.randomUUID(),"minecraft:overworld|7,101,1");
        var unresolved=new PickupTransactionJournal.View(
            existing, PickupTransactionJournal.State.UNRESOLVED);
        var cargo=new PickupTransactionJournal.View(
            existing, PickupTransactionJournal.State.CARGO_RETURNED);
        var empty=new PickupTransactionJournal.View(
            existing, PickupTransactionJournal.State.EXTRACTION_EMPTY);
        check(PickupSourceAdmission.classify(List.of(),sameSource)
            == PickupSourceAdmission.Decision.ALLOW_NO_CONFLICT);
        check(PickupSourceAdmission.classify(List.of(unresolved),sameSource)
            == PickupSourceAdmission.Decision.DENY_UNRESOLVED_EXTRACTION);
        check(PickupSourceAdmission.classify(List.of(cargo),sameSource)
            == PickupSourceAdmission.Decision.DENY_UNRECONCILED_CARGO);
        check(PickupSourceAdmission.classify(List.of(empty),sameSource)
            == PickupSourceAdmission.Decision.ALLOW_NO_CONFLICT);
        check(PickupSourceAdmission.classify(List.of(unresolved,cargo),sameSource)
            == PickupSourceAdmission.Decision.DENY_UNRESOLVED_EXTRACTION);
        check(PickupSourceAdmission.classify(List.of(unresolved),otherSource)
            == PickupSourceAdmission.Decision.ALLOW_NO_CONFLICT);
        check(PickupSourceAdmission.classify(List.of(cargo),otherSource)
            == PickupSourceAdmission.Decision.ALLOW_NO_CONFLICT);
        check(PickupSourceAdmission.classify(List.of(empty),existing)
            == PickupSourceAdmission.Decision.DENY_REUSED_JOB_ID);
        check(PickupSourceAdmission.classify(List.of(cargo),
                intent(UUID.randomUUID(),UUID.randomUUID(),existing.source()))
            == PickupSourceAdmission.Decision.DENY_INVALID_REQUEST);
        check(PickupSourceAdmission.classify(null,sameSource)
            == PickupSourceAdmission.Decision.DENY_INVALID_REQUEST);
        System.out.println("PickupSourceAdmissionTest passed");
    }
}
