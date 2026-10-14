package dev.hearthbound.ai;

import java.util.Comparator;
import java.util.Optional;

import static dev.hearthbound.ai.ColonyPolicy.*;

/** Deterministic B0 benchmark. Larger needs signal more urgency. */
public final class PriorityPolicy implements ColonyPolicy {
    @Override
    public Decision choose(Observation o) {
        Optional<Action> selected = o.availableActions().stream()
            .filter(Action::executable)
            .max(Comparator.comparingInt((Action a) -> score(o, a))
                .thenComparing(a -> a.id(), Comparator.reverseOrder()));
        return selected.map(a -> new Decision(o.version(), a.id(), "B0 priority policy"))
            .orElse(new Decision(o.version(), "", "No executable action; do nothing"));
    }

    private static int score(Observation o, Action a) {
        int urgency = switch (a.kind()) {
            case FLEE -> o.danger() >= 60 ? 1000 : -1000;
            case EAT -> o.hunger() >= 70 ? 900 : -100;
            case REST -> o.fatigue() >= 80 ? 800 : -100;
            case DELIVER -> 350;
            case OPERATE -> 300;
            case HAUL -> 250;
            case FOLLOW -> 200;
            case IDLE -> -500;
        };
        return urgency + a.priority();
    }
}
