package dev.hearthbound.ai;

import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * Deterministic, server-authoritative reservation state machine.
 * In-memory prototype: not a crash-safe persistent item transaction ledger.
 */
public final class HaulLedger {
    public enum State { RESERVED, IN_TRANSIT, COMPLETE, CANCELLED }
    public record Ticket(UUID id, String actor, String source, String destination,
                         State state, int units) {
        public Ticket {
            Objects.requireNonNull(id);
            Objects.requireNonNull(actor);
            Objects.requireNonNull(source);
            Objects.requireNonNull(destination);
            Objects.requireNonNull(state);
            if (units <= 0 || source.equals(destination)) throw new IllegalArgumentException("invalid transfer");
        }
    }
    private final Map<UUID, Ticket> tickets = new HashMap<>();
    private final Map<String, UUID> reservedSources = new HashMap<>();

    public synchronized Ticket reserve(String actor, String source, String destination, int units) {
        if (reservedSources.containsKey(source)) throw new IllegalStateException("source reserved");
        UUID id = UUID.randomUUID();
        Ticket ticket = new Ticket(id, actor, source, destination, State.RESERVED, units);
        tickets.put(id, ticket);
        reservedSources.put(source, id);
        return ticket;
    }

    public synchronized Ticket transition(UUID id, State expected, State next) {
        Ticket old = Objects.requireNonNull(tickets.get(id), "unknown ticket");
        if (old.state != expected) throw new IllegalStateException("stale transfer state");
        boolean allowed = expected == State.RESERVED && (next == State.IN_TRANSIT || next == State.CANCELLED)
            || expected == State.IN_TRANSIT && next == State.COMPLETE;
        if (!allowed) throw new IllegalStateException("illegal transition");
        Ticket updated = new Ticket(old.id, old.actor, old.source, old.destination, next, old.units);
        tickets.put(id, updated);
        if (next == State.COMPLETE || next == State.CANCELLED) reservedSources.remove(old.source, id);
        return updated;
    }

    public synchronized Ticket get(UUID id) { return tickets.get(id); }
    public synchronized int outstanding() {
        return (int) tickets.values().stream().filter(t -> t.state == State.RESERVED || t.state == State.IN_TRANSIT).count();
    }
}
