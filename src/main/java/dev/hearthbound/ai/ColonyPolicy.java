package dev.hearthbound.ai;

import java.util.List;
import java.util.Objects;

/**
 * Pure Java policy boundary. The Minecraft server constructs observations and
 * must validate the returned choice again before performing any world mutation.
 */
public interface ColonyPolicy {
    Decision choose(Observation observation);

    record Action(String id, Kind kind, int priority, boolean executable) {
        public Action {
            Objects.requireNonNull(id, "id");
            Objects.requireNonNull(kind, "kind");
            if (id.isBlank()) throw new IllegalArgumentException("blank action id");
        }
    }

    enum Kind { EAT, FLEE, REST, HAUL, OPERATE, DELIVER, IDLE }

    record Observation(long version, String citizenId, int hunger, int danger,
                       int fatigue, List<Action> availableActions) {
        public Observation {
            if (version < 0) throw new IllegalArgumentException("negative version");
            Objects.requireNonNull(citizenId, "citizenId");
            if (citizenId.isBlank()) throw new IllegalArgumentException("blank citizen id");
            if (hunger < 0 || hunger > 100 || danger < 0 || danger > 100 ||
                fatigue < 0 || fatigue > 100) {
                throw new IllegalArgumentException("needs must be in [0,100]");
            }
            availableActions = List.copyOf(availableActions);
            if (availableActions.stream().map(Action::id).distinct().count() != availableActions.size())
                throw new IllegalArgumentException("duplicate action id");
        }
    }

    record Decision(long expectedVersion, String actionId, String rationale) {
        public Decision {
            Objects.requireNonNull(actionId, "actionId");
            Objects.requireNonNull(rationale, "rationale");
        }
    }
}
