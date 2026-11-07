package dev.hearthbound.world;

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
        if (level == null || source == null || sender == null || recipient == null)
            throw new IllegalArgumentException("missing exchange arguments");
        if (!citizen(sender) || !citizen(recipient) || sender.getUUID().equals(recipient.getUUID()))
            return "KNOWLEDGE_SHARE ABSTAIN reason=INVALID_PARTICIPANTS action_authorized=false";
        if (sender.level() != level || recipient.level() != level ||
            sender.distanceToSqr(recipient) > COMMUNICATION_RANGE * COMMUNICATION_RANGE)
            return "KNOWLEDGE_SHARE ABSTAIN reason=OUT_OF_RANGE action_authorized=false";

        CompoundTag evidence = CitizenSourceKnowledge.directEvidence(level, source, sender);
        if (evidence == null)
            return "KNOWLEDGE_SHARE ABSTAIN reason=NO_DIRECT_EVIDENCE action_authorized=false";
        long observed = evidence.getLong("observed_tick");
        long delivered = level.getGameTime();
        if (observed > delivered || delivered - observed > CitizenSourceKnowledge.FRESH_TICKS)
            return "KNOWLEDGE_SHARE ABSTAIN reason=STALE_SOURCE action_authorized=false";

        CompoundTag root = recipient.getPersistentData().getCompound(ROOT);
        ListTag entries = root.getList(ENTRIES, Tag.TAG_COMPOUND);
        // One report per source/sender/observation revision: replay is idempotent.
        String reportId = sender.getUUID() + "|" + evidence.getString("source")
            + "|" + evidence.getInt("revision");
        for (int i = 0; i < entries.size(); i++) {
            if (reportId.equals(entries.getCompound(i).getString("id")))
                return "KNOWLEDGE_SHARE status=DUPLICATE action_authorized=false";
        }
        ListTag updated = new ListTag();
        for (int i = 0; i < entries.size(); i++) {
            CompoundTag previous = entries.getCompound(i);
            long age = delivered - previous.getLong("delivered_tick");
            if (age >= 0 && age <= REPORT_TTL_TICKS) updated.add(previous.copy());
        }
        while (updated.size() >= MAX_REPORTS) updated.remove(0);
        CompoundTag report = new CompoundTag();
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
        return "KNOWLEDGE_SHARE status=DELIVERED source=" + key(level, source)
            + " sender=" + sender.getUUID() + " recipient=" + recipient.getUUID()
            + " observed_tick=" + observed + " delivered_tick=" + delivered
            + " action_authorized=false";
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
            if (!key(level, source).equals(r.getString("source"))
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
        return newest.copy();
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
