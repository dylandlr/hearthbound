package dev.hearthbound.world;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import dev.hearthbound.civilization.CommunicationJournal;
import dev.hearthbound.civilization.CommunicationJournal.Event;
import dev.hearthbound.civilization.CommunicationJournal.Message;
import dev.hearthbound.civilization.CommunicationJournal.Stage;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Consumer;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * Observational, server-thread history of actual report delivery and consumption.
 * This history never supplies policy inputs, grants rewards, or authorizes a motor.
 * SavedData is ordinary save persistence, not a crash-atomic inventory journal.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class CitizenCommunicationRecords {
    public static final String SCHEMA = "hearthbound.citizen-communication.v1";
    private static final String STORAGE = "hearthbound_citizen_communication_v1";
    private static final int MAX_MESSAGES = 1024;
    private static final int MAX_EVENTS = 8192;
    private static final int MAX_SEND_ATTEMPTS = 2048;
    private CitizenCommunicationRecords() {}

    private static final class History extends SavedData {
        CommunicationJournal journal = new CommunicationJournal(MAX_MESSAGES, MAX_EVENTS);
        final Map<UUID, CompoundTag> jobs = new LinkedHashMap<>();
        final Map<UUID, CompoundTag> attempts = new LinkedHashMap<>();
        long sendAttempts;
        long rejectedSends;
        long duplicateSends;
        long recordingErrors;
        long attemptCapacityDenials;
        CompoundTag invalidSavedHistory;

        static History load(CompoundTag root) {
            History result = new History();
            try {
                if (!SCHEMA.equals(root.getString("schema")))
                    throw new IllegalArgumentException("Unsupported communication history");
                if (root.contains("invalidSavedHistory")) {
                    require(root, "invalidSavedHistory", Tag.TAG_COMPOUND);
                    result.invalidSavedHistory = root.getCompound("invalidSavedHistory").copy();
                    result.recordingErrors = nonnegative(root, "recordingErrors");
                    return result;
                }
                List<Message> messages = new ArrayList<>();
                for (Tag value : compoundList(root, "messages")) {
                    CompoundTag m = (CompoundTag) value;
                    require(m, "reportId", Tag.TAG_STRING); require(m, "source", Tag.TAG_STRING);
                    require(m, "wheat", Tag.TAG_INT); require(m, "sourceRevision", Tag.TAG_INT);
                    require(m, "observed", Tag.TAG_LONG); require(m, "sent", Tag.TAG_LONG);
                    require(m, "delivered", Tag.TAG_LONG);
                    messages.add(new Message(m.getUUID("id"), m.getUUID("world"),
                        m.getUUID("episode"), m.getUUID("sender"), m.getUUID("recipient"),
                        m.getString("reportId"), m.getString("source"), m.getInt("wheat"),
                        m.getInt("sourceRevision"), m.getLong("observed"), m.getLong("sent"),
                        m.getLong("delivered")));
                }
                List<Event> events = new ArrayList<>();
                for (Tag value : compoundList(root, "events")) {
                    CompoundTag e = (CompoundTag) value;
                    require(e, "sequence", Tag.TAG_LONG); require(e, "stage", Tag.TAG_STRING);
                    require(e, "tick", Tag.TAG_LONG);
                    events.add(new Event(e.getLong("sequence"), Stage.valueOf(e.getString("stage")),
                        e.getUUID("message"), e.getUUID("actor"),
                        e.hasUUID("decision") ? e.getUUID("decision") : null,
                        e.hasUUID("job") ? e.getUUID("job") : null, e.getLong("tick")));
                }
                result.journal = CommunicationJournal.restore(MAX_MESSAGES, MAX_EVENTS,
                    messages, events, nonnegative(root, "capacityDenials"));
                result.sendAttempts = nonnegative(root, "sendAttempts");
                result.rejectedSends = nonnegative(root, "rejectedSends");
                result.duplicateSends = nonnegative(root, "duplicateSends");
                result.recordingErrors = nonnegative(root, "recordingErrors");
                result.attemptCapacityDenials = nonnegative(root, "attemptCapacityDenials");
                for (Tag value : compoundList(root, "sendRecords")) {
                    CompoundTag attempt = (CompoundTag) value;
                    require(attempt, "source", Tag.TAG_STRING); require(attempt, "tick", Tag.TAG_LONG);
                    require(attempt, "outcome", Tag.TAG_STRING); require(attempt, "reason", Tag.TAG_STRING);
                    if (!attempt.hasUUID("sender") || !attempt.hasUUID("recipient")
                            || !attempt.hasUUID("world") || !attempt.hasUUID("episode")
                            || attempt.getLong("tick") < 0
                            || !List.of("REQUESTED", "REJECTED", "DUPLICATE", "DELIVERED")
                                .contains(attempt.getString("outcome"))
                            || result.attempts.putIfAbsent(attempt.getUUID("id"), attempt.copy()) != null
                            || result.attempts.size() > MAX_SEND_ATTEMPTS)
                        throw new IllegalArgumentException("Invalid persisted send attempt");
                }
                for (Tag value : compoundList(root, "jobs")) {
                    CompoundTag job = (CompoundTag) value;
                    UUID id = job.getUUID("job");
                    require(job, "source", Tag.TAG_LONG); require(job, "destination", Tag.TAG_LONG);
                    require(job, "assigned", Tag.TAG_LONG);
                    boolean bound = events.stream().anyMatch(e -> e.stage() == Stage.ASSIGNED
                        && id.equals(e.jobId()) && job.getUUID("citizen").equals(e.actor())
                        && job.getUUID("decision").equals(e.decisionId())
                        && job.getUUID("message").equals(e.messageId())
                        && job.getLong("assigned") == e.tick());
                    if (!bound || job.getLong("source") == job.getLong("destination")
                            || result.jobs.putIfAbsent(id, job.copy()) != null)
                        throw new IllegalArgumentException("Invalid communication job binding");
                }
                long assignments = events.stream().filter(e -> e.stage() == Stage.ASSIGNED).count();
                if (assignments != result.jobs.size())
                    throw new IllegalArgumentException("Missing communication job binding");
            } catch (RuntimeException corrupt) {
                // Retain the original bytes in SavedData and make incompleteness visible.
                // Bad research telemetry must never stop physical Minecraft work.
                result = new History();
                result.invalidSavedHistory = root.copy();
                result.recordingErrors = 1;
            }
            return result;
        }

        @Override public CompoundTag save(CompoundTag root) {
            root.putString("schema", SCHEMA);
            if (invalidSavedHistory != null) {
                root.put("invalidSavedHistory", invalidSavedHistory.copy());
                root.putLong("recordingErrors", recordingErrors);
                return root;
            }
            ListTag messages = new ListTag();
            for (Message m : journal.messages()) {
                CompoundTag t = new CompoundTag();
                t.putUUID("id", m.id()); t.putUUID("world", m.world()); t.putUUID("episode", m.episode());
                t.putUUID("sender", m.sender()); t.putUUID("recipient", m.recipient());
                t.putString("reportId", m.reportId()); t.putString("source", m.source());
                t.putInt("wheat", m.wheat()); t.putInt("sourceRevision", m.sourceRevision());
                t.putLong("observed", m.observedTick()); t.putLong("sent", m.sentTick());
                t.putLong("delivered", m.deliveredTick()); messages.add(t);
            }
            ListTag events = new ListTag();
            for (Event e : journal.events()) {
                CompoundTag t = new CompoundTag();
                t.putLong("sequence", e.sequence()); t.putString("stage", e.stage().name());
                t.putUUID("message", e.messageId()); t.putUUID("actor", e.actor());
                if (e.decisionId() != null) t.putUUID("decision", e.decisionId());
                if (e.jobId() != null) t.putUUID("job", e.jobId());
                t.putLong("tick", e.tick()); events.add(t);
            }
            ListTag bindings = new ListTag();
            jobs.values().forEach(t -> bindings.add(t.copy()));
            root.put("messages", messages); root.put("events", events); root.put("jobs", bindings);
            ListTag sends = new ListTag();
            attempts.values().forEach(t -> sends.add(t.copy()));
            root.put("sendRecords", sends);
            root.putLong("capacityDenials", journal.capacityDenials());
            root.putLong("sendAttempts", sendAttempts); root.putLong("rejectedSends", rejectedSends);
            root.putLong("duplicateSends", duplicateSends); root.putLong("recordingErrors", recordingErrors);
            root.putLong("attemptCapacityDenials", attemptCapacityDenials);
            return root;
        }
    }

    private static void require(CompoundTag tag, String key, int type) {
        if (!tag.contains(key, type)) throw new IllegalArgumentException("Missing communication field " + key);
    }

    private static ListTag compoundList(CompoundTag tag, String key) {
        require(tag, key, Tag.TAG_LIST);
        ListTag list = (ListTag) tag.get(key);
        if (!list.isEmpty() && list.getElementType() != Tag.TAG_COMPOUND)
            throw new IllegalArgumentException("Invalid communication list " + key);
        return list;
    }

    private static long nonnegative(CompoundTag tag, String key) {
        require(tag, key, Tag.TAG_LONG);
        long value = tag.getLong(key);
        if (value < 0) throw new IllegalArgumentException("Negative communication counter");
        return value;
    }

    private static History data(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(History::load, History::new, STORAGE);
    }

    private static void record(ServerLevel level, Consumer<History> operation) {
        History history = null;
        try {
            history = data(level);
            if (history.invalidSavedHistory != null) history.recordingErrors++;
            else operation.accept(history);
        } catch (RuntimeException invalid) {
            if (history != null) history.recordingErrors++;
            org.slf4j.LoggerFactory.getLogger(CitizenCommunicationRecords.class)
                .warn("Communication evidence could not be recorded: {}", invalid.toString());
        } finally {
            if (history != null) history.setDirty();
        }
    }

    static UUID sendAttempt(ServerLevel level, BlockPos source, Villager sender, Villager recipient) {
        UUID id = UUID.randomUUID();
        record(level, h -> {
            h.sendAttempts++;
            if (h.attempts.size() >= MAX_SEND_ATTEMPTS) { h.attemptCapacityDenials++; return; }
            CompoundTag attempt = new CompoundTag();
            attempt.putUUID("id", id); attempt.putUUID("world", HearthboundWorldIdentity.get(level));
            attempt.putUUID("episode", SourceReportSession.episode(level));
            attempt.putUUID("sender", sender.getUUID()); attempt.putUUID("recipient", recipient.getUUID());
            attempt.putString("source", ReportChoiceCommands.key(level, source));
            attempt.putLong("tick", level.getGameTime());
            attempt.putString("outcome", "REQUESTED"); attempt.putString("reason", "UNRESOLVED");
            h.attempts.put(id, attempt);
        });
        return id;
    }

    private static void sendOutcome(History h, UUID id, String outcome, String reason, String reportId) {
        CompoundTag attempt = h.attempts.get(id);
        if (attempt == null) return; // The visible attempt-capacity/error counter explains missing rows.
        if (!"REQUESTED".equals(attempt.getString("outcome")))
            throw new IllegalArgumentException("Conflicting send outcome");
        attempt.putString("outcome", outcome); attempt.putString("reason", reason);
        if (reportId != null) attempt.putString("reportId", reportId);
    }

    static void rejected(ServerLevel level, UUID attempt, String reason) {
        record(level, h -> { h.rejectedSends++; sendOutcome(h, attempt, "REJECTED", reason, null); });
    }

    static void duplicate(ServerLevel level, UUID attempt, String reportId) {
        record(level, h -> { h.duplicateSends++; sendOutcome(h, attempt, "DUPLICATE", "ALREADY_DELIVERED", reportId); });
    }

    private static UUID messageId(ServerLevel level, UUID recipient, String reportId) {
        return UUID.nameUUIDFromBytes((SourceReportSession.episode(level) + "|" + recipient + "|"
            + reportId).getBytes(StandardCharsets.UTF_8));
    }

    static void delivered(ServerLevel level, UUID attempt, CompoundTag report) {
        record(level, h -> {
            sendOutcome(h, attempt, "DELIVERED", "ACCEPTED_RECIPIENT_INBOX", report.getString("id"));
            h.journal.delivered(new Message(
            messageId(level, report.getUUID("recipient"), report.getString("id")),
            HearthboundWorldIdentity.get(level), SourceReportSession.episode(level),
            report.getUUID("sender"), report.getUUID("recipient"), report.getString("id"),
            report.getString("source"), report.getInt("wheat"), report.getInt("source_revision"),
            report.getLong("observed_tick"), report.getLong("delivered_tick"),
            report.getLong("delivered_tick")));
        });
    }

    /** Called only by a real dispatch evaluation, never by a shadow/audit query. */
    static void read(ServerLevel level, Villager recipient, UUID decision, CompoundTag report) {
        if (decision == null) return;
        record(level, h -> h.journal.read(messageId(level, recipient.getUUID(), report.getString("id")),
            recipient.getUUID(), decision, level.getGameTime()));
    }

    static void selected(ServerLevel level, Villager recipient, UUID decision, String reportId, long tick) {
        record(level, h -> h.journal.selected(messageId(level, recipient.getUUID(), reportId),
            recipient.getUUID(), decision, tick));
    }

    static void assigned(ServerLevel level, Villager recipient, UUID decision, String reportId,
                         UUID job, long source, long destination, long tick) {
        record(level, h -> {
            UUID message = messageId(level, recipient.getUUID(), reportId);
            if (h.journal.assigned(message, recipient.getUUID(), decision, job, tick)) {
                CompoundTag binding = new CompoundTag();
                binding.putUUID("job", job); binding.putUUID("message", message);
                binding.putUUID("decision", decision); binding.putUUID("citizen", recipient.getUUID());
                binding.putLong("source", source); binding.putLong("destination", destination);
                binding.putLong("assigned", tick);
                h.jobs.putIfAbsent(job, binding);
            }
        });
    }

    /** Called after SableHauling's actual insertion success and claim release. */
    static void physicalCompleted(ServerLevel level, Villager citizen) {
        CompoundTag haul = citizen.getPersistentData().getCompound("hearthbound.haul");
        CompoundTag receipt = haul.getCompound("reportPolicyDispatch.v1");
        if (!receipt.hasUUID("communicationDecision")) return; // older/unrelated jobs are uninstrumented
        record(level, h -> {
            UUID job = haul.getUUID("jobId");
            CompoundTag binding = h.jobs.get(job);
            if (binding == null) throw new IllegalArgumentException("Missing observed assignment");
            Message message = h.journal.messages().stream()
                .filter(m -> m.id().equals(binding.getUUID("message"))).findFirst().orElseThrow();
            if (!message.world().equals(HearthboundWorldIdentity.get(level))
                    || !message.episode().equals(SourceReportSession.episode(level))
                    || !message.recipient().equals(citizen.getUUID())
                    || !message.reportId().equals(receipt.getString("reportId"))
                    || !receipt.getUUID("communicationDecision").equals(binding.getUUID("decision")))
                throw new IllegalArgumentException("Foreign communication assignment");
            SableHauling.Assignment actual = SableHauling.completedAssignment(level, citizen, job,
                BlockPos.of(binding.getLong("destination")));
            if (actual.source() != binding.getLong("source")
                    || actual.assignedTick() != binding.getLong("assigned"))
                throw new IllegalArgumentException("Physical communication assignment mismatch");
            h.journal.completed(job, citizen.getUUID(), haul.getLong("physicalDeliveredTick"));
        });
    }

    private static long count(History history, Stage stage) {
        return history.journal.events().stream().filter(e -> e.stage() == stage).count();
    }

    private static String audit(ServerLevel level) {
        History h = data(level);
        return "CITIZEN_COMMUNICATION_AUDIT_V1 world=" + HearthboundWorldIdentity.get(level)
            + " episode=" + SourceReportSession.episode(level)
            + " send_attempts=" + h.sendAttempts + " rejected_sends=" + h.rejectedSends
            + " duplicate_sends=" + h.duplicateSends + " messages=" + h.journal.messages().size()
            + " events=" + h.journal.events().size() + " delivered=" + count(h, Stage.DELIVERED)
            + " read=" + count(h, Stage.READ) + " selected=" + count(h, Stage.SELECTED)
            + " assigned=" + count(h, Stage.ASSIGNED) + " physical_completed=" + count(h, Stage.PHYSICAL_COMPLETED)
            + " capacity_denials=" + h.journal.capacityDenials() + " recording_errors=" + h.recordingErrors
            + " send_records=" + h.attempts.size() + " attempt_capacity_denials=" + h.attemptCapacityDenials
            + " history_quarantined=" + (h.invalidSavedHistory != null)
            + " strictly_read_only=true causal_benefit_established=false reward_authorized=false";
    }

    private static JsonObject page(ServerLevel level, String kind, int offset) {
        JsonObject root = new JsonObject();
        root.addProperty("schema", SCHEMA); root.addProperty("world", HearthboundWorldIdentity.get(level).toString());
        root.addProperty("dimension", level.dimension().location().toString());
        root.addProperty("kind", kind); root.addProperty("offset", offset);
        root.addProperty("strictly_read_only", true); root.addProperty("causal_benefit_established", false);
        root.addProperty("inventory_delta_verified", false);
        return root;
    }

    private static String messages(ServerLevel level, int offset) {
        List<Message> all = data(level).journal.messages();
        JsonObject root = page(level, "messages", offset);
        root.addProperty("total", all.size());
        JsonArray rows = new JsonArray();
        for (int i = offset; i < Math.min(all.size(), offset + 4); i++) {
            Message m = all.get(i); JsonObject row = new JsonObject();
            row.addProperty("id", m.id().toString()); row.addProperty("world", m.world().toString());
            row.addProperty("episode", m.episode().toString()); row.addProperty("sender", m.sender().toString());
            row.addProperty("recipient", m.recipient().toString()); row.addProperty("report_id", m.reportId());
            row.addProperty("source", m.source()); row.addProperty("reported_wheat", m.wheat());
            row.addProperty("source_revision", m.sourceRevision()); row.addProperty("observed_tick", m.observedTick());
            row.addProperty("sent_tick", m.sentTick()); row.addProperty("delivered_tick", m.deliveredTick());
            row.addProperty("expires_after_tick", m.deliveredTick() + CitizenKnowledgeExchange.REPORT_TTL_TICKS);
            row.addProperty("transport", "EXPLICIT_LOCAL_SYNCHRONOUS"); rows.add(row);
        }
        root.add("records", rows);
        return "CITIZEN_COMMUNICATION_MESSAGES_V1 " + root;
    }

    private static String events(ServerLevel level, int offset) {
        History h = data(level); List<Event> all = h.journal.events();
        JsonObject root = page(level, "events", offset); root.addProperty("total", all.size());
        JsonArray rows = new JsonArray();
        for (int i = offset; i < Math.min(all.size(), offset + 8); i++) {
            Event e = all.get(i); JsonObject row = new JsonObject();
            row.addProperty("sequence", e.sequence()); row.addProperty("stage", e.stage().name());
            row.addProperty("message_id", e.messageId().toString()); row.addProperty("actor", e.actor().toString());
            if (e.decisionId() != null) row.addProperty("decision_id", e.decisionId().toString());
            if (e.jobId() != null) {
                row.addProperty("job_id", e.jobId().toString());
                CompoundTag binding = h.jobs.get(e.jobId());
                if (binding != null) row.addProperty("destination", ReportChoiceCommands.key(level,
                    BlockPos.of(binding.getLong("destination"))));
            }
            if (e.stage() == Stage.PHYSICAL_COMPLETED) {
                row.addProperty("wheat_transferred", 1);
                row.addProperty("witness", "EXECUTOR_INSERTION_RETURNED_NO_REMAINDER");
            }
            row.addProperty("tick", e.tick()); rows.add(row);
        }
        root.add("records", rows);
        return "CITIZEN_COMMUNICATION_EVENTS_V1 " + root;
    }

    private static String attempts(ServerLevel level, int offset) {
        List<CompoundTag> all = List.copyOf(data(level).attempts.values());
        JsonObject root = page(level, "attempts", offset); root.addProperty("total", all.size());
        JsonArray rows = new JsonArray();
        for (int i = offset; i < Math.min(all.size(), offset + 4); i++) {
            CompoundTag attempt = all.get(i); JsonObject row = new JsonObject();
            for (String key : List.of("id", "world", "episode", "sender", "recipient"))
                row.addProperty(key, attempt.getUUID(key).toString());
            for (String key : List.of("source", "outcome", "reason"))
                row.addProperty(key, attempt.getString(key));
            row.addProperty("tick", attempt.getLong("tick"));
            if (attempt.contains("reportId")) row.addProperty("report_id", attempt.getString("reportId"));
            rows.add(row);
        }
        root.add("records", rows);
        return "CITIZEN_COMMUNICATION_ATTEMPTS_V1 " + root;
    }

    @SubscribeEvent public static void registerCommands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("hearthbound-communication")
            .requires(s -> s.hasPermission(2))
            .then(Commands.literal("audit").executes(ctx -> {
                ctx.getSource().sendSuccess(() -> Component.literal(audit(ctx.getSource().getLevel())), false);
                return 1;
            }))
            .then(Commands.literal("messages").then(Commands.argument("offset", IntegerArgumentType.integer(0))
                .executes(ctx -> {
                    ctx.getSource().sendSuccess(() -> Component.literal(messages(ctx.getSource().getLevel(),
                        IntegerArgumentType.getInteger(ctx, "offset"))), false); return 1;
                })))
            .then(Commands.literal("events").then(Commands.argument("offset", IntegerArgumentType.integer(0))
                .executes(ctx -> {
                    ctx.getSource().sendSuccess(() -> Component.literal(events(ctx.getSource().getLevel(),
                        IntegerArgumentType.getInteger(ctx, "offset"))), false); return 1;
                })))
            .then(Commands.literal("attempts").then(Commands.argument("offset", IntegerArgumentType.integer(0))
                .executes(ctx -> {
                    ctx.getSource().sendSuccess(() -> Component.literal(attempts(ctx.getSource().getLevel(),
                        IntegerArgumentType.getInteger(ctx, "offset"))), false); return 1;
                }))));
    }
}
