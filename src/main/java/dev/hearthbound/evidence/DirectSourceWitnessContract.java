package dev.hearthbound.evidence;

import java.util.Objects;
import java.util.UUID;

/**
 * Pure Java contract for an independently observed source that actually gates
 * an operator-assigned hauling task. This does NOT establish that the observer
 * selected the task, originated a recipe, or deserves a research reward.
 */
public final class DirectSourceWitnessContract {
    public static final String DIRECT = "DIRECT_FORGE_OBSERVATION";
    public static final int MAX_OBSERVATION_AGE_TICKS = 40;
    private DirectSourceWitnessContract() {}

    public record DirectSource(UUID world, UUID observer, String dimension, long position,
                               long observedTick, int sourceRevision, int wheat, String origin) {
        public DirectSource {
            Objects.requireNonNull(world);
            Objects.requireNonNull(observer);
            if (dimension == null || dimension.isBlank() || origin == null
                    || observedTick < 0 || sourceRevision < 1 || wheat <= 0)
                throw new IllegalArgumentException("invalid physical source observation");
        }
    }

    public record WitnessLink(UUID world, UUID job, UUID executor, UUID observer,
                              String dimension, long position, long observedTick,
                              long assignedTick, int sourceRevision, int wheat,
                              String origin, String evidenceId) {
        public WitnessLink {
            Objects.requireNonNull(world);
            Objects.requireNonNull(job);
            Objects.requireNonNull(executor);
            Objects.requireNonNull(observer);
            if (executor.equals(observer) || dimension == null || dimension.isBlank()
                    || observedTick < 0 || assignedTick < observedTick
                    || assignedTick - observedTick > MAX_OBSERVATION_AGE_TICKS
                    || sourceRevision < 1 || wheat <= 0 || !DIRECT.equals(origin))
                throw new IllegalArgumentException("not a fresh independent direct witness");
            if (!identity(world, dimension, position, job, observer,
                    observedTick, sourceRevision).equals(evidenceId))
                throw new IllegalArgumentException("noncanonical witness identity");
        }
    }

    private static String identity(UUID world, String dimension, long source, UUID job,
                                   UUID observer, long observed, int revision) {
        return "hearthbound:source-witness:v1:" + world + ":" + dimension
                + ":" + source + ":" + job + ":" + observer + ":"
                + observed + ":" + revision;
    }

    /** Pure validation of a direct pre-task source observation. */
    public static WitnessLink bind(DirectSource direct, UUID job, UUID executor,
                                    String dimension, long source, long assignedTick) {
        Objects.requireNonNull(direct);
        Objects.requireNonNull(job);
        Objects.requireNonNull(executor);
        if (!DIRECT.equals(direct.origin()) || !dimension.equals(direct.dimension())
                || direct.position() != source || direct.observer().equals(executor)
                || assignedTick < direct.observedTick()
                || assignedTick - direct.observedTick() > MAX_OBSERVATION_AGE_TICKS)
            throw new IllegalArgumentException("report, other source, self or stale witness");
        return new WitnessLink(direct.world(), job, executor, direct.observer(),
            dimension, source, direct.observedTick(), assignedTick,
            direct.sourceRevision(), direct.wheat(), direct.origin(),
            identity(direct.world(), dimension, source, job, direct.observer(),
                direct.observedTick(), direct.sourceRevision()));
    }

    /**
     * A joined process verifies provenance of the original assignment gate,
     * but does NOT establish autonomous choice or a share of research reward.
     * The original direct-memory revision must still match the witness NBT.
     */
    public static boolean matchesProcess(WitnessLink link, DirectSource direct, UUID world,
                                         UUID job, UUID executor, String dimension,
                                         long source, long assignedTick,
                                         long processStartTick) {
        if (link == null || direct == null || world == null || job == null
                || executor == null || dimension == null) return false;
        if (processStartTick <= assignedTick) return false;
        try {
            WitnessLink expected = bind(direct, job, executor, dimension, source, assignedTick);
            return world.equals(link.world()) && world.equals(direct.world())
                && link.equals(expected);
        } catch (IllegalArgumentException | NullPointerException invalid) {
            return false;
        }
    }
}
