package dev.hearthbound.research;

import java.util.Objects;
import java.util.UUID;

/**
 * Versioned citizen inventory snapshot owned by server-side simulation state.
 * Immutable transitions are suitable for persistence by a separate adapter.
 */
public final class CitizenInventory {
    public record State(UUID citizenId, int wheat) {
        public State {
            Objects.requireNonNull(citizenId);
            if (wheat < 0) throw new IllegalArgumentException("Negative wheat");
        }
    }
    public record Transfer(State next, int count) {}
    public static Transfer reserveWheat(State current, UUID authorizedCitizen, int requested) {
        Objects.requireNonNull(current);
        Objects.requireNonNull(authorizedCitizen);
        if (!current.citizenId().equals(authorizedCitizen) || requested != 1
                || current.wheat() < requested)
            throw new IllegalArgumentException("Unauthorized or unavailable wheat");
        return new Transfer(new State(current.citizenId(), current.wheat() - requested), requested);
    }
    private CitizenInventory() {}
}
