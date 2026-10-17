package dev.hearthbound.ai;

import java.util.List;
import java.util.Objects;
import java.util.UUID;
import static dev.hearthbound.ai.ColonyPolicy.*;

/**
 * Deterministic and stochastic policy arbitration across executable offers.
 * This pure-Java planner has no authority to create physical work.
 */
public final class WorkChoicePlanner {
    public record Offer(String id, Kind kind, int priority, boolean available) {
        public Offer {
            Objects.requireNonNull(id);
            Objects.requireNonNull(kind);
            if (id.isBlank()) throw new IllegalArgumentException("Blank work id");
            if (priority < 0 || priority > 100) throw new IllegalArgumentException("Invalid offer priority");
        }
    }
    private WorkChoicePlanner() {}

    public static Observation observation(UUID citizen, long gameTick,
                                          int hunger, int danger, int fatigue,
                                          List<Offer> offers) {
        Objects.requireNonNull(citizen);
        Objects.requireNonNull(offers);
        return new Observation(gameTick, citizen.toString(), hunger, danger, fatigue,
                offers.stream().map(o -> new Action(o.id(), o.kind(),
                        o.priority(), o.available())).toList());
    }

    public static Decision choose(Observation snapshot, ColonyPolicy policy) {
        Objects.requireNonNull(policy);
        Decision selected = policy.choose(snapshot);
        if (!ActionGate.allowed(snapshot, selected))
            return new Decision(snapshot.version(), "", "No authorized executable work");
        return selected;
    }
}
