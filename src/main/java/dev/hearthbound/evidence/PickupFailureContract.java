package dev.hearthbound.evidence;

import java.util.Objects;
import java.util.UUID;

/**
 * A negative motor observation made ONLY when an actual source extraction
 * returned no cargo. Not proof that a chest is empty, a path failed, or a
 * recipient deserves research reward.
 */
public final class PickupFailureContract {
    public static final String SCHEMA = "hearthbound.pickup-failure.v1";
    public static final String OBSERVATION = "REAL_SOURCE_EXTRACTION_RETURNED_EMPTY";
    private PickupFailureContract() {}

    public record Failure(UUID world, UUID job, UUID executor, String source,
                          String selectedReportId, long assignedTick,
                          long failedTick, String observation) {
        public Failure {
            Objects.requireNonNull(world);
            Objects.requireNonNull(job);
            Objects.requireNonNull(executor);
            if (source == null || source.isBlank() || selectedReportId == null
                    || selectedReportId.isBlank() || "NONE".equals(selectedReportId)
                    || assignedTick < 0 || failedTick < assignedTick
                    || !OBSERVATION.equals(observation))
                throw new IllegalArgumentException("invalid physical pickup failure");
        }
    }

    public record Report(String source, String id, long observedTick, long deliveredTick) {
        public Report {
            if (source == null || source.isBlank() || id == null || id.isBlank()
                    || observedTick < 0 || deliveredTick < observedTick)
                throw new IllegalArgumentException("invalid delivered source report");
        }
    }

    /** An old report cannot be reused merely by changing its delivery time. */
    public static boolean disqualifies(Failure failure, UUID world, UUID actor, Report report) {
        if (failure == null || world == null || actor == null || report == null)
            return false;
        return failure.world().equals(world) && failure.executor().equals(actor)
            && failure.source().equals(report.source())
            && (failure.selectedReportId().equals(report.id())
                || report.observedTick() <= failure.failedTick());
    }

    /** The job and report must refer to the same actual failed extraction. */
    public static boolean matches(Failure failure, UUID world, UUID job,
                                  UUID actor, String source, String reportId,
                                  long assignedTick, long failedTick) {
        return failure != null && Objects.equals(world, failure.world())
            && Objects.equals(job, failure.job())
            && Objects.equals(actor, failure.executor())
            && Objects.equals(source, failure.source())
            && Objects.equals(reportId, failure.selectedReportId())
            && failure.assignedTick() == assignedTick
            && failure.failedTick() == failedTick;
    }
}
