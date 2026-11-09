package dev.hearthbound.evidence;

import java.util.*;

/**
 * Read-only join between persisted journal entries and LOADED Minecraft
 * executor snapshots. Missing loaded data is UNKNOWN, never evidence that a
 * citizen is absent or its inventory is empty. No execution permission here.
 */
public final class PickupCitizenReconciliation {
    private PickupCitizenReconciliation() {}

    public record Citizen(UUID executor, UUID job, boolean reportPolicyJob,
                          boolean cargoPresent, boolean cargoQuarantined) {
        public Citizen {
            Objects.requireNonNull(executor);
            Objects.requireNonNull(job);
        }
    }
    public enum Status {
        NOT_LOADED,
        NO_MATCHING_SAVED_JOB,
        MATCHED_EMPTY_OUTCOME,
        MATCHED_UNRESOLVED,
        MATCHED_CARGO_OUTCOME,
        WRONG_JOB_OR_POLICY,
        CARGO_CONTRADICTION
    }
    public record Row(UUID job, UUID executor, Status status) {}
    public record Summary(List<Row> rows, int notLoaded, int mismatched, int heldForReview) {
        public Summary { rows = List.copyOf(rows); }
    }

    public static Summary inspect(List<PickupTransactionJournal.View> journal,
                                  List<Citizen> loaded) {
        Objects.requireNonNull(journal);
        Objects.requireNonNull(loaded);
        Map<UUID, Citizen> byActor = new HashMap<>();
        Set<UUID> ambiguous = new HashSet<>();
        for (Citizen citizen : loaded) {
            if (byActor.putIfAbsent(citizen.executor(), citizen) != null)
                ambiguous.add(citizen.executor());
        }
        List<Row> result = new ArrayList<>();
        int unknown = 0, bad = 0, hold = 0;
        for (PickupTransactionJournal.View event : journal) {
            PickupTransactionJournal.Intent intent = event.intent();
            Citizen citizen = byActor.get(intent.executor());
            Status status;
            if (citizen == null) status = Status.NOT_LOADED;
            else if (ambiguous.contains(intent.executor())
                    || !citizen.job().equals(intent.job())
                    || !citizen.reportPolicyJob())
                status = Status.WRONG_JOB_OR_POLICY;
            else if (citizen.cargoPresent()
                    && event.state() == PickupTransactionJournal.State.EXTRACTION_EMPTY)
                status = Status.CARGO_CONTRADICTION;
            else if (event.state() == PickupTransactionJournal.State.UNRESOLVED)
                status = Status.MATCHED_UNRESOLVED;
            else if (event.state() == PickupTransactionJournal.State.CARGO_RETURNED)
                status = Status.MATCHED_CARGO_OUTCOME;
            else status = Status.MATCHED_EMPTY_OUTCOME;
            if (status == Status.NOT_LOADED) unknown++;
            else if (status == Status.WRONG_JOB_OR_POLICY
                    || status == Status.CARGO_CONTRADICTION) bad++;
            if (status != Status.MATCHED_EMPTY_OUTCOME) hold++;
            result.add(new Row(intent.job(), intent.executor(), status));
        }
        return new Summary(result, unknown, bad, hold);
    }
}
