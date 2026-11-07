package dev.hearthbound.evidence;

import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;

/**
 * Pre-action, report-conditioned SOURCE SELECTION baseline.
 *
 * Two experimental arms can receive exactly the same candidate set while
 * one is denied the recipient's own previously delivered reports.
 * This policy does NOT inspect Minecraft, issue jobs, predict actual
 * inventory, award rewards, or claim learned cooperation.
 */
public final class ReportConditionedChoice {
    public static final int MAX_REPORT_AGE_TICKS = 200;
    public static final int MAX_SOURCE_AGE_AT_DELIVERY = 40;
    public static final String ORIGIN = "REPORTED_DIRECT_FORGE_OBSERVATION";
    public enum Exposure { WITHHELD, EXPOSED }
    public enum Status { ABSTAIN, CHOOSE }

    public record Report(String source, UUID recipient, UUID sender,
                         String origin, String state, int wheat,
                         int revision, long observedTick, long deliveredTick) {}

    public record Decision(Status status, String source, String reason,
                           int admissibleReports, Exposure exposure,
                           boolean observedWorldInventory) {
        public Decision {
            Objects.requireNonNull(status);
            Objects.requireNonNull(reason);
            Objects.requireNonNull(exposure);
            if (status == Status.CHOOSE && (source == null || source.isBlank()))
                throw new IllegalArgumentException("missing chosen source");
            if (status == Status.ABSTAIN && source != null)
                throw new IllegalArgumentException("abstaining may not claim a source");
            if (observedWorldInventory)
                throw new IllegalArgumentException("report-conditioned selection read world truth");
        }
    }

    private ReportConditionedChoice() {}

    public static Decision choose(UUID recipient, List<String> candidates,
                                  List<Report> reports, Exposure exposure, long decisionTick) {
        Objects.requireNonNull(recipient);
        Objects.requireNonNull(candidates);
        Objects.requireNonNull(reports);
        Objects.requireNonNull(exposure);
        if (decisionTick < 0 || candidates.isEmpty() || candidates.size() > 8
                || new HashSet<>(candidates).size() != candidates.size()
                || candidates.stream().anyMatch(s -> s == null || s.isBlank()))
            throw new IllegalArgumentException("invalid pre-action source menu");
        // WITHHELD means even an existing recipient report cannot influence
        // the policy. This condition never reads the contents of reports.
        if (exposure == Exposure.WITHHELD)
            return new Decision(Status.ABSTAIN, null, "REPORT_EXPOSURE_WITHHELD",
                0, exposure, false);
        Set<String> menu = Set.copyOf(candidates);
        int accepted=0, bestWheat=-1;
        String best=null;
        for (Report report : reports) {
            if (report == null || report.source() == null || !menu.contains(report.source())
                    || !recipient.equals(report.recipient())
                    || report.sender() == null || report.sender().equals(recipient)
                    || !ORIGIN.equals(report.origin())
                    || !"AVAILABLE".equals(report.state()) || report.wheat() <= 0
                    || report.revision() < 1 || report.observedTick() < 0
                    || report.observedTick() > report.deliveredTick()
                    || report.deliveredTick() > decisionTick
                    || report.deliveredTick() - report.observedTick() > MAX_SOURCE_AGE_AT_DELIVERY
                    || decisionTick - report.deliveredTick() > MAX_REPORT_AGE_TICKS)
                continue;
            accepted++;
            // Ranking is an explicit SCRIPTED baseline, not a trained MLP.
            // Use lexical identity as deterministic tie breaker.
            if (report.wheat() > bestWheat || (report.wheat() == bestWheat
                    && (best == null || report.source().compareTo(best) < 0))) {
                bestWheat=report.wheat();
                best=report.source();
            }
        }
        return best == null
            ? new Decision(Status.ABSTAIN,null,"NO_FRESH_ADMISSIBLE_REPORT",0,exposure,false)
            : new Decision(Status.CHOOSE,best,"SCRIPTED_HIGHEST_REPORTED_WHEAT",
                accepted,exposure,false);
    }
}
