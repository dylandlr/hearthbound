package dev.hearthbound.civilization;

import java.util.Objects;
import java.util.UUID;

/** Read-only projection of one loaded citizen's most recent verified physical job. */
public final class ColonyDecisionTrace {
    private ColonyDecisionTrace() {}

    public record Trace(long taskId, UUID citizen, UUID job, UUID episode,
                        UUID decision, UUID evidence, long revision,
                        long observedTick, long decisionTick, long assignedTick,
                        long deliveredTick, String action, String target,
                        String policy) {
        public Trace {
            Objects.requireNonNull(citizen);
            Objects.requireNonNull(job);
            Objects.requireNonNull(episode);
            Objects.requireNonNull(decision);
            Objects.requireNonNull(evidence);
            Objects.requireNonNull(action);
            Objects.requireNonNull(target);
            Objects.requireNonNull(policy);
        }
    }

    /** Reject stale, superseded, different-episode, or nonphysical claims. */
    public static boolean valid(Trace t, UUID currentEpisode, long nowTick) {
        return t != null && currentEpisode != null
            && currentEpisode.equals(t.episode())
            && t.taskId() > 0 && t.revision() >= 1
            && t.observedTick() >= 0
            && t.observedTick() <= t.decisionTick()
            && t.decisionTick() <= t.assignedTick()
            && t.assignedTick() <= t.deliveredTick()
            && t.deliveredTick() <= nowTick
            && t.assignedTick() - t.observedTick()
                <= CivilizationContracts.MAX_GATHER_EVIDENCE_AGE_TICKS
            && "GATHER".equals(t.action())
            && "DETERMINISTIC_TRAIT_RANK_V1".equals(t.policy())
            && !t.target().isBlank();
    }

    /** Delimiter-safe identity/tick fields only; never exposes raw citizen NBT. */
    public static String encode(Trace t) {
        if (t == null) throw new IllegalArgumentException("missing trace");
        return t.taskId() + "," + t.citizen() + "," + t.job() + ","
            + t.decision() + "," + t.evidence() + ","
            + t.revision() + "," + t.observedTick() + ","
            + t.decisionTick() + "," + t.assignedTick() + ","
            + t.deliveredTick();
    }
}
