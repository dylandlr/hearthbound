package dev.hearthbound.evidence;

import java.util.*;

public final class PickupCitizenReconciliationTest {
    private static void check(boolean v) { if (!v) throw new AssertionError(); }
    public static void main(String[] args) {
        UUID world = UUID.randomUUID(), actor = UUID.randomUUID(), job = UUID.randomUUID();
        var intent = new PickupTransactionJournal.Intent(
            world, job, actor, "overworld|2,64,3", "report-id", 10, 11);
        var empty = new PickupTransactionJournal.View(
            intent, PickupTransactionJournal.State.EXTRACTION_EMPTY);
        var cargo = new PickupTransactionJournal.View(
            intent, PickupTransactionJournal.State.CARGO_RETURNED);
        var pending = new PickupTransactionJournal.View(
            intent, PickupTransactionJournal.State.UNRESOLVED);
        var unloaded = PickupCitizenReconciliation.inspect(List.of(pending), List.of());
        check(unloaded.notLoaded() == 1 && unloaded.heldForReview() == 1);
        check(unloaded.rows().get(0).status() == PickupCitizenReconciliation.Status.NOT_LOADED);
        var citizen = new PickupCitizenReconciliation.Citizen(actor, job, true, false, false);
        check(PickupCitizenReconciliation.inspect(List.of(empty), List.of(citizen))
            .rows().get(0).status() == PickupCitizenReconciliation.Status.MATCHED_EMPTY_OUTCOME);
        check(PickupCitizenReconciliation.inspect(List.of(cargo), List.of(citizen))
            .rows().get(0).status() == PickupCitizenReconciliation.Status.MATCHED_CARGO_OUTCOME);
        check(PickupCitizenReconciliation.inspect(List.of(pending), List.of(citizen))
            .rows().get(0).status() == PickupCitizenReconciliation.Status.MATCHED_UNRESOLVED);
        var unexpectedCargo = new PickupCitizenReconciliation.Citizen(actor, job, true, true, false);
        check(PickupCitizenReconciliation.inspect(List.of(empty), List.of(unexpectedCargo))
            .rows().get(0).status() == PickupCitizenReconciliation.Status.CARGO_CONTRADICTION);
        var wrongJob = new PickupCitizenReconciliation.Citizen(actor, UUID.randomUUID(), true, false, false);
        check(PickupCitizenReconciliation.inspect(List.of(empty), List.of(wrongJob))
            .rows().get(0).status() == PickupCitizenReconciliation.Status.WRONG_JOB_OR_POLICY);
        check(PickupCitizenReconciliation.inspect(List.of(empty), List.of(citizen, citizen))
            .mismatched() == 1);
        check(PickupCitizenReconciliation.inspect(List.of(empty), List.of())
            .rows().get(0).status() != PickupCitizenReconciliation.Status.MATCHED_EMPTY_OUTCOME);
        System.out.println("PickupCitizenReconciliationTest passed");
    }
}
