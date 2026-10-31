package dev.hearthbound.evidence;

import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

/** Server-side physical processing receipt validator. Does not infer recipe success. */
public final class ProcessingEvidenceGate {
    public record Receipt(String eventId, String dimension, String machineId,
                          String recipeId, String inputItem, String outputItem,
                          long beforeInput, long afterInput,
                          long beforeOutput, long afterOutput,
                          long startTick, long finishTick,
                          boolean machineLoaded, boolean serverObserved) {}
    public interface CreditSink { void accept(Receipt receipt); }
    public enum Result { ACCEPTED, DUPLICATE, INVALID, UNVERIFIED }
    private final Set<String> committed = new HashSet<>();
    private final CreditSink sink;
    public ProcessingEvidenceGate(CreditSink sink) { this.sink = Objects.requireNonNull(sink); }
    /** Invoke on the authoritative server thread. */
    public synchronized Result submit(Receipt r) {
        if (r == null || blank(r.eventId()) || blank(r.dimension()) || blank(r.machineId())
                || blank(r.recipeId()) || blank(r.inputItem()) || blank(r.outputItem())
                || r.startTick() < 0 || r.finishTick() <= r.startTick()
                || r.beforeInput() < 0 || r.afterInput() < 0 || r.beforeOutput() < 0 || r.afterOutput() < 0)
            return Result.INVALID;
        if (committed.contains(r.eventId())) return Result.DUPLICATE;
        if (!r.machineLoaded() || !r.serverObserved()
                || r.afterInput() >= r.beforeInput() || r.afterOutput() <= r.beforeOutput())
            return Result.UNVERIFIED;
        // Sink is responsible for atomic, durable event-ID uniqueness and reward credit.
        sink.accept(r);
        committed.add(r.eventId());
        return Result.ACCEPTED;
    }
    /** Restore known committed IDs from the durable ledger before processing events. */
    public synchronized void restoreCommitted(Iterable<String> eventIds) {
        for (String id : eventIds) {
            if (blank(id)) throw new IllegalArgumentException("empty committed ID");
            committed.add(id);
        }
    }
    private static boolean blank(String s) { return s == null || s.isBlank(); }
}
