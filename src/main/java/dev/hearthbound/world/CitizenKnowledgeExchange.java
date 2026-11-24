package dev.hearthbound.world;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Explicit, local, read-only citizen-to-citizen knowledge exchange.
 * Reports are private to recipient; they never become direct observations.
 * No autonomy, inventory access, chunk loading or task authorization.
 */
public final class CitizenKnowledgeExchange {
    public static final String SCHEMA = "hearthbound.citizen-reports.v1";
    private static final String ROOT = "hearthbound.citizen_reports.v1";
    private static final String ENTRIES = "entries";
    public static final int MAX_REPORTS = 16;
    public static final int COMMUNICATION_RANGE = 12;
    public static final long REPORT_TTL_TICKS = 200L;
    private CitizenKnowledgeExchange() {}

    private static String key(ServerLevel level, BlockPos source) {
        return level.dimension().location() + "|" + source.getX() + "," +
            source.getY() + "," + source.getZ();
    }

    private static boolean citizen(Villager v) {
        return v != null && (v.getPersistentData().getBoolean("hearthbound.sable")
            || v.getPersistentData().getBoolean("hearthbound.citizen"));
    }

    /**
     * Sender must possess a direct observation of this source.
     * Transfer is explicit, range checked and never re-samples world truth.
     */
    public static String share(ServerLevel level, BlockPos source, Villager sender, Villager recipient) {
        return shareWithReceipt(level, source, sender, recipient).result();
    }

    /** Exact identity of the one recorded attempt; does not add another send. */
    record ShareReceipt(UUID attempt, String result) {}

    static ShareReceipt shareWithReceipt(ServerLevel level, BlockPos source,
                                        Villager sender, Villager recipient) {
        if (level == null || source == null || sender == null || recipient == null)
            throw new IllegalArgumentException("missing exchange arguments");
        UUID attempt = CitizenCommunicationRecords.sendAttempt(level, source, sender, recipient);
        return new ShareReceipt(attempt, shareAttempt(level, source, sender, recipient, attempt));
    }

    private static String shareAttempt(ServerLevel level, BlockPos source,
                                       Villager sender, Villager recipient, UUID attempt) {
        if (!citizen(sender) || !citizen(recipient) || sender.getUUID().equals(recipient.getUUID()))
            return rejected(level, attempt, "INVALID_PARTICIPANTS");
        if (sender.level() != level || recipient.level() != level ||
            sender.distanceToSqr(recipient) > COMMUNICATION_RANGE * COMMUNICATION_RANGE)
            return rejected(level, attempt, "OUT_OF_RANGE");

        CompoundTag evidence = CitizenSourceKnowledge.directEvidence(level, source, sender);
        if (evidence == null)
            return rejected(level, attempt, "NO_DIRECT_EVIDENCE");
        long observed = evidence.getLong("observed_tick");
        long delivered = level.getGameTime();
        if (!SourceReportSession.accepts(level, evidence, delivered))
            return rejected(level, attempt, "REOBSERVATION_REQUIRED_AFTER_RESTART");
        if (observed > delivered || delivered - observed > CitizenSourceKnowledge.FRESH_TICKS)
            return rejected(level, attempt, "STALE_SOURCE");

        CompoundTag root = recipient.getPersistentData().getCompound(ROOT);
        ListTag entries = root.getList(ENTRIES, Tag.TAG_COMPOUND);
        // Identity includes the DIRECT OBSERVATION TICK, not just the
        // state revision. Reobserving an unchanged physical source is a new
        // evidence event; retransmitting the SAME event remains idempotent.
        // A new delivery timestamp alone never creates a new event.
        String reportId = sender.getUUID() + "|" + evidence.getString("source")
            + "|" + evidence.getInt("revision")
            + "|" + observed + "|" + evidence.getUUID("observationWorld")
            + "|" + evidence.getUUID("observationSession");
        for (int i = 0; i < entries.size(); i++) {
            if (reportId.equals(entries.getCompound(i).getString("id"))) {
                CitizenCommunicationRecords.duplicate(level, attempt, reportId);
                return "KNOWLEDGE_SHARE status=DUPLICATE action_authorized=false";
            }
        }
        ListTag updated = new ListTag();
        for (int i = 0; i < entries.size(); i++) {
            CompoundTag previous = entries.getCompound(i);
            long age = delivered - previous.getLong("delivered_tick");
            if (age >= 0 && age <= REPORT_TTL_TICKS) updated.add(previous.copy());
        }
        while (updated.size() >= MAX_REPORTS) updated.remove(0);
        CompoundTag report = new CompoundTag();
        report.putUUID("observationWorld", evidence.getUUID("observationWorld"));
        report.putUUID("observationSession", evidence.getUUID("observationSession"));
        report.putString("id", reportId);
        report.putString("source", evidence.getString("source"));
        report.putString("state", evidence.getString("state"));
        report.putInt("wheat", evidence.getInt("wheat"));
        report.putLong("observed_tick", observed);
        report.putLong("delivered_tick", delivered);
        report.putInt("source_revision", evidence.getInt("revision"));
        report.putUUID("sender", sender.getUUID());
        report.putUUID("recipient", recipient.getUUID());
        report.putString("origin", "REPORTED_DIRECT_FORGE_OBSERVATION");
        updated.add(report);
        root.putString("schema", SCHEMA);
        root.put(ENTRIES, updated);
        recipient.getPersistentData().put(ROOT, root);
        CitizenCommunicationRecords.delivered(level, attempt, report);
        // Only a brand-new delivered direct observation with observation
        // tick strictly after the recipient's real failed extraction can
        // fulfill an explicitly requested source recheck.
        SourceFailureBeliefs.fulfillAfterExplicitShare(level, recipient, source, report);
        return "KNOWLEDGE_SHARE status=DELIVERED source=" + key(level, source)
            + " sender=" + sender.getUUID() + " recipient=" + recipient.getUUID()
            + " observed_tick=" + observed + " delivered_tick=" + delivered
            + " action_authorized=false";
    }

    private static String rejected(ServerLevel level, UUID attempt, String reason) {
        CitizenCommunicationRecords.rejected(level, attempt, reason);
        return "KNOWLEDGE_SHARE ABSTAIN reason=" + reason + " action_authorized=false";
    }

    /**
     * A recipient-owned, previously delivered REPORT, not current world truth.
     * Used for a read-only decision experiment. Does not force-load a chunk,
     * consult sender memory, read any inventory or authorize physical work.
     */
    public static CompoundTag decisionReport(ServerLevel level, BlockPos source, Villager recipient) {
        if (level == null || source == null || recipient == null
                || recipient.level() != level || !citizen(recipient))
            return null;
        ListTag reports = recipient.getPersistentData().getCompound(ROOT)
            .getList(ENTRIES, Tag.TAG_COMPOUND);
        CompoundTag newest = null;
        long now = level.getGameTime();
        for (int i = 0; i < reports.size(); i++) {
            CompoundTag r = reports.getCompound(i);
            long delivered = r.getLong("delivered_tick");
            long observed = r.getLong("observed_tick");
            if (!SourceReportSession.accepts(level, r, delivered)
                    || !key(level, source).equals(r.getString("source"))
                    || !"REPORTED_DIRECT_FORGE_OBSERVATION".equals(r.getString("origin"))
                    || (!"AVAILABLE".equals(r.getString("state"))
                        && !"EMPTY".equals(r.getString("state")))
                    || !r.hasUUID("recipient") || !r.getUUID("recipient").equals(recipient.getUUID())
                    || !r.hasUUID("sender") || r.getUUID("sender").equals(recipient.getUUID())
                    || r.getInt("wheat") < 0 || r.getInt("source_revision") < 1
                    || observed < 0 || observed > delivered
                    || delivered > now || now - delivered > REPORT_TTL_TICKS
                    || delivered - observed > CitizenSourceKnowledge.FRESH_TICKS)
                continue;
            // Later EMPTY observations supersede older AVAILABLE evidence,
            // even when the two reports share a Minecraft game tick.
            if (newest == null || delivered >= newest.getLong("delivered_tick"))
                newest = r;
        }
        if (newest == null || !"AVAILABLE".equals(newest.getString("state"))
                || newest.getInt("wheat") <= 0) return null;
        // A real pickup attempt can refute a previously delivered source
        // report. Do not edit the historical report or sample world truth.
        // Only a new direct observation strictly AFTER that failure can
        // re-enable the source for the same executor.
        if (!SourceFailureBeliefs.acceptsReport(level, recipient, source, newest))
            return null;
        return newest.copy();
    }

    /**
     * Enumerate only this recipient's actually delivered private source reports.
     * Unlike decisionReport, no public source-coordinate menu is required. EMPTY
     * reports remain visible so an older AVAILABLE report cannot be resurrected.
     * Enumeration is not a policy READ event; the consuming policy records that.
     * Callers must apply their common direct/report observation-age rule.
     */
    public static List<CompoundTag> decisionReports(ServerLevel level, Villager recipient) {
        if (level == null || recipient == null || recipient.level() != level || !citizen(recipient))
            return List.of();
        ListTag reports = recipient.getPersistentData().getCompound(ROOT)
            .getList(ENTRIES, Tag.TAG_COMPOUND);
        // The real transport never creates a larger inbox. Do not turn edited
        // or malformed persistent state into an unbounded policy input.
        if (reports.size() > MAX_REPORTS) return List.of();
        var newest = new LinkedHashMap<String, CompoundTag>();
        long now = level.getGameTime();
        for (int i = 0; i < reports.size(); i++) {
            CompoundTag report = reports.getCompound(i);
            BlockPos source = reportedSource(level, report);
            if (source == null || !report.contains("id", Tag.TAG_STRING)
                    || report.getString("id").isBlank()
                    || !report.contains("delivered_tick", Tag.TAG_LONG)
                    || !report.contains("wheat", Tag.TAG_INT)
                    || !report.contains("source_revision", Tag.TAG_INT)) continue;
            long delivered = report.getLong("delivered_tick");
            long observed = report.getLong("observed_tick");
            boolean available = "AVAILABLE".equals(report.getString("state"));
            boolean empty = "EMPTY".equals(report.getString("state"));
            if (!SourceReportSession.accepts(level, report, delivered)
                    || !"REPORTED_DIRECT_FORGE_OBSERVATION".equals(report.getString("origin"))
                    || (!available && !empty)
                    || (available ? report.getInt("wheat") <= 0 : report.getInt("wheat") != 0)
                    || !report.hasUUID("recipient")
                    || !report.getUUID("recipient").equals(recipient.getUUID())
                    || !report.hasUUID("sender") || report.getUUID("sender").equals(recipient.getUUID())
                    || report.getInt("source_revision") < 1
                    || observed < 0 || observed > delivered || delivered > now
                    || now - delivered > REPORT_TTL_TICKS
                    || delivered - observed > CitizenSourceKnowledge.FRESH_TICKS) continue;
            CompoundTag prior = newest.get(report.getString("source"));
            if (prior == null || observed > prior.getLong("observed_tick")
                    || (observed == prior.getLong("observed_tick")
                        && delivered >= prior.getLong("delivered_tick")))
                newest.put(report.getString("source"), report);
        }
        var result = new ArrayList<CompoundTag>();
        for (CompoundTag report : newest.values()) {
            if ("AVAILABLE".equals(report.getString("state"))
                    && !SourceFailureBeliefs.acceptsReport(level, recipient,
                        reportedSource(level, report), report)) continue;
            result.add(report.copy());
        }
        return List.copyOf(result);
    }

    /** Parse a canonical same-dimension source key without consulting the world. */
    static BlockPos reportedSource(ServerLevel level, CompoundTag report) {
        String prefix = level.dimension().location() + "|";
        String source = report.getString("source");
        if (!source.startsWith(prefix)) return null;
        String[] parts = source.substring(prefix.length()).split(",", -1);
        if (parts.length != 3) return null;
        try {
            BlockPos position = new BlockPos(Integer.parseInt(parts[0]),
                Integer.parseInt(parts[1]), Integer.parseInt(parts[2]));
            return key(level, position).equals(source) ? position : null;
        } catch (NumberFormatException invalid) {
            return null;
        }
    }

    /** Operator inspection, never pulls current inventory or sender's private data. */
    public static String inspect(ServerLevel level, BlockPos source, Villager recipient) {
        if (level == null || source == null || recipient == null)
            throw new IllegalArgumentException("missing report query");
        String prefix = "CITIZEN_REPORT schema=" + SCHEMA + " citizen="
            + recipient.getUUID() + " source=" + key(level, source);
        if (!citizen(recipient))
            return prefix + " status=DENIED action_authorized=false";
        ListTag entries = recipient.getPersistentData().getCompound(ROOT)
            .getList(ENTRIES, Tag.TAG_COMPOUND);
        CompoundTag newest = null;
        for (int i = 0; i < entries.size(); i++) {
            CompoundTag candidate = entries.getCompound(i);
            if (!key(level, source).equals(candidate.getString("source"))) continue;
            if (newest == null || candidate.getLong("delivered_tick") > newest.getLong("delivered_tick"))
                newest = candidate;
        }
        if (newest == null) return prefix + " status=UNKNOWN action_authorized=false";
        long age = level.getGameTime() - newest.getLong("delivered_tick");
        String freshness = age >= 0 && age <= REPORT_TTL_TICKS ? "RETAINED" : "EXPIRED";
        return prefix + " status=REPORTED freshness=" + freshness
            + " state=" + newest.getString("state")
            + " wheat=" + newest.getInt("wheat")
            + " observed_tick=" + newest.getLong("observed_tick")
            + " delivered_tick=" + newest.getLong("delivered_tick")
            + " sender=" + newest.getUUID("sender")
            + " origin=REPORTED_DIRECT_FORGE_OBSERVATION action_authorized=false";
    }
}
