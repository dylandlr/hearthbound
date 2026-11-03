package dev.hearthbound.evidence;

import java.util.Objects;

/**
 * Read-only versioned policy selector for millstone task suggestions.
 * It cannot issue tasks, access Minecraft, alter rewards, or mutate world state.
 */
public final class MillPolicyShadow {
    private MillPolicyShadow() {}

    public enum Mode { SCRIPTED, TRAINED_MLP }
    public enum Action {
        INSPECT_UNPOWERED, COLLECT_OUTPUT, WAIT_FOR_PROCESSING, REQUEST_WHEAT_HAUL
    }
    public record Observation(boolean powered, boolean wheatPresent, boolean flourPresent,
                              boolean blocked, long experience) {
        public Observation {
            if (experience < 0) throw new IllegalArgumentException("negative verified experience");
        }
    }
    public record Decision(Mode mode, Action reference, Action rawMlp,
                           Action selected, boolean disagreement, boolean masked) {
        public Decision {
            Objects.requireNonNull(mode);
            Objects.requireNonNull(reference);
            Objects.requireNonNull(rawMlp);
            Objects.requireNonNull(selected);
        }
    }

    public static Action reference(Observation o) {
        Objects.requireNonNull(o);
        if (!o.powered()) return Action.INSPECT_UNPOWERED;
        if (o.flourPresent() || o.blocked()) return Action.COLLECT_OUTPUT;
        if (o.wheatPresent()) return Action.WAIT_FOR_PROCESSING;
        return Action.REQUEST_WHEAT_HAUL;
    }

    /** Minimal high-level action mask. Not a substitute for execution-time checks. */
    public static boolean allowed(Observation o, Action a) {
        Objects.requireNonNull(o);
        Objects.requireNonNull(a);
        if (!o.powered()) return a == Action.INSPECT_UNPOWERED;
        return switch (a) {
            case INSPECT_UNPOWERED -> false;
            case COLLECT_OUTPUT -> o.flourPresent() || o.blocked();
            case WAIT_FOR_PROCESSING -> o.wheatPresent() && !o.flourPresent() && !o.blocked();
            case REQUEST_WHEAT_HAUL -> !o.wheatPresent() && !o.flourPresent() && !o.blocked();
        };
    }

    public static Decision decide(Mode mode, Observation obs, MillMlpInference model) {
        Objects.requireNonNull(mode);
        Objects.requireNonNull(obs);
        Objects.requireNonNull(model);
        Action reference=reference(obs);
        Action raw=Action.valueOf(model.predict(obs.powered(), obs.wheatPresent(),
            obs.flourPresent(), obs.blocked(), obs.experience()).name());
        // Explicit, auditable safety fallback. Shadow decisions never execute.
        boolean masked=!allowed(obs,raw);
        Action selected=mode == Mode.SCRIPTED ? reference : masked ? reference : raw;
        return new Decision(mode,reference,raw,selected,raw != reference,masked);
    }
}
