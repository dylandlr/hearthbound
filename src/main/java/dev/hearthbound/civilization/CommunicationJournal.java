package dev.hearthbound.civilization;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Bounded observation history for a delivered citizen report and its use.
 *
 * A read is a policy input, selection is a decision, assignment is an accepted
 * motor job, and physical completion must come from that job's trusted receipt.
 * None of these records establish a causal benefit, grant inventory authority,
 * or authorize rewards. Persistence is supplied by the caller; this class is
 * not a crash-atomic transaction journal.
 */
public final class CommunicationJournal {
    public enum Stage { DELIVERED, READ, SELECTED, ASSIGNED, PHYSICAL_COMPLETED }

    public record Message(UUID id, UUID world, UUID episode, UUID sender,
                          UUID recipient, String reportId, String source,
                          int wheat, int sourceRevision, long observedTick,
                          long sentTick, long deliveredTick) {
        public Message {
            require(id != null && world != null && episode != null
                && sender != null && recipient != null, "Missing message identity");
            require(!sender.equals(recipient), "A citizen report requires another recipient");
            require(text(reportId) && text(source), "Missing or oversized report provenance");
            require(wheat >= 0 && sourceRevision >= 1 && observedTick >= 0
                && sentTick >= observedTick && deliveredTick >= sentTick,
                "Invalid message observation or delivery chronology");
        }
    }

    public record Event(long sequence, Stage stage, UUID messageId, UUID actor,
                        UUID decisionId, UUID jobId, long tick) {
        public Event {
            require(sequence >= 1 && stage != null && messageId != null
                && actor != null && tick >= 0, "Invalid communication event");
            switch (stage) {
                case DELIVERED -> require(decisionId == null && jobId == null,
                    "Delivery cannot imply a decision or job");
                case READ, SELECTED -> require(decisionId != null && jobId == null,
                    "Read and selection require a decision but no job");
                case ASSIGNED, PHYSICAL_COMPLETED -> require(decisionId != null && jobId != null,
                    "Job events require their original decision and job");
            }
        }
    }

    private record DeliveryKey(UUID world, UUID episode, UUID recipient, String reportId) {}
    private record DecisionMessage(UUID decision, UUID message) {}
    private record DecisionScope(UUID actor, UUID world, UUID episode) {}

    private final int maxMessages;
    private final int maxEvents;
    private final Map<UUID, Message> messages = new LinkedHashMap<>();
    private final Map<DeliveryKey, UUID> deliveryKeys = new HashMap<>();
    private final List<Event> events = new ArrayList<>();
    private final Map<DecisionMessage, Event> reads = new HashMap<>();
    private final Map<UUID, DecisionScope> decisionScopes = new HashMap<>();
    private final Map<UUID, Long> lastReadTicks = new HashMap<>();
    private final Map<UUID, Event> selections = new HashMap<>();
    private final Map<UUID, Event> assignments = new HashMap<>();
    private final Map<UUID, Event> decisionAssignments = new HashMap<>();
    private final Map<UUID, Event> completions = new HashMap<>();
    private long capacityDenials;

    public CommunicationJournal(int maxMessages, int maxEvents) {
        require(maxMessages >= 1 && maxMessages <= 65536
            && maxEvents >= 1 && maxEvents <= 1048576,
            "Invalid communication history bounds");
        this.maxMessages = maxMessages;
        this.maxEvents = maxEvents;
    }

    /** True includes exact replay; false means a counted capacity denial. */
    public synchronized boolean delivered(Message message) {
        require(message != null, "Missing delivered report");
        Message previous = messages.get(message.id());
        if (previous != null) {
            require(previous.equals(message), "Conflicting message replay");
            return true;
        }
        DeliveryKey key = deliveryKey(message);
        require(!deliveryKeys.containsKey(key), "Delivered report cannot be renamed and counted twice");
        // Reserve both slots before recording either half of the delivery.
        if (messages.size() >= maxMessages || events.size() >= maxEvents)
            return denied();
        Event event = next(Stage.DELIVERED, message, null, null, message.deliveredTick());
        messages.put(message.id(), message);
        deliveryKeys.put(key, message.id());
        events.add(event);
        return true;
    }

    /** Only call from an actual policy evaluation, never an operator inspection. */
    public synchronized boolean read(UUID messageId, UUID recipient, UUID decision, long tick) {
        Message message = recipientMessage(messageId, recipient);
        require(decision != null && tick >= message.deliveredTick(), "Read precedes delivery");
        checkDecisionScope(message, decision);
        DecisionMessage key = new DecisionMessage(decision, messageId);
        Event previous = reads.get(key);
        if (previous != null) return replay(previous, message, recipient, decision, null, tick);
        require(!selections.containsKey(decision), "Decision inputs are closed after selection");
        if (events.size() >= maxEvents) return denied();
        Event event = next(Stage.READ, message, decision, null, tick);
        events.add(event);
        reads.put(key, event);
        decisionScopes.put(decision, scope(message));
        lastReadTicks.merge(decision, tick, Math::max);
        return true;
    }

    public synchronized boolean selected(UUID messageId, UUID recipient, UUID decision, long tick) {
        Message message = recipientMessage(messageId, recipient);
        require(decision != null, "Missing decision identity");
        checkDecisionScope(message, decision);
        Event previous = selections.get(decision);
        if (previous != null) return replay(previous, message, recipient, decision, null, tick);
        Event read = reads.get(new DecisionMessage(decision, messageId));
        require(read != null && tick >= read.tick()
            && tick >= lastReadTicks.getOrDefault(decision, Long.MAX_VALUE),
            "Selection requires its earlier policy reads");
        if (events.size() >= maxEvents) return denied();
        Event event = next(Stage.SELECTED, message, decision, null, tick);
        events.add(event);
        selections.put(decision, event);
        return true;
    }

    public synchronized boolean assigned(UUID messageId, UUID recipient, UUID decision,
                                         UUID job, long tick) {
        Message message = recipientMessage(messageId, recipient);
        require(decision != null && job != null, "Missing assignment identity");
        checkDecisionScope(message, decision);
        Event previous = assignments.get(job);
        if (previous != null) return replay(previous, message, recipient, decision, job, tick);
        require(!decisionAssignments.containsKey(decision), "Decision already assigned another job");
        Event selected = selections.get(decision);
        require(selected != null && selected.messageId().equals(messageId)
            && tick >= selected.tick(), "Assignment requires the selected report");
        if (events.size() >= maxEvents) return denied();
        Event event = next(Stage.ASSIGNED, message, decision, job, tick);
        events.add(event);
        assignments.put(job, event);
        decisionAssignments.put(decision, event);
        return true;
    }

    /** Caller must verify the actual hauling job and pass its physical delivery tick. */
    public synchronized boolean completed(UUID job, UUID citizen, long tick) {
        require(job != null && citizen != null, "Missing completion identity");
        Event assigned = assignments.get(job);
        require(assigned != null, "Completion cannot reconstruct a missing assignment");
        Message message = recipientMessage(assigned.messageId(), citizen);
        require(tick >= assigned.tick(), "Physical completion precedes assignment");
        Event previous = completions.get(job);
        if (previous != null)
            return replay(previous, message, citizen, assigned.decisionId(), job, tick);
        if (events.size() >= maxEvents) return denied();
        Event event = next(Stage.PHYSICAL_COMPLETED, message, assigned.decisionId(), job, tick);
        events.add(event);
        completions.put(job, event);
        return true;
    }

    public synchronized List<Message> messages() { return List.copyOf(messages.values()); }
    public synchronized List<Event> events() { return List.copyOf(events); }
    public synchronized long capacityDenials() { return capacityDenials; }
    public int maxMessages() { return maxMessages; }
    public int maxEvents() { return maxEvents; }

    /**
     * Reconstruct exactly the recorded append order, validating every lifecycle.
     * Tick order is required along each decision/job chain. A delayed physical
     * receipt may carry an earlier tick than an unrelated event appended first.
     * A corrupt, duplicate, gapped, or over-capacity input is rejected whole.
     */
    public static CommunicationJournal restore(int maxMessages, int maxEvents,
            List<Message> messages, List<Event> events, long capacityDenials) {
        require(messages != null && events != null && capacityDenials >= 0,
            "Invalid communication snapshot");
        CommunicationJournal journal = new CommunicationJournal(maxMessages, maxEvents);
        require(messages.size() <= maxMessages && events.size() <= maxEvents,
            "Restored communication history exceeds capacity");
        Map<UUID, Message> declared = new HashMap<>();
        for (Message message : messages) {
            require(message != null && declared.putIfAbsent(message.id(), message) == null,
                "Duplicate restored message identity");
        }
        long sequence = 0;
        for (Event event : events) {
            require(event != null && event.sequence() == ++sequence,
                "Communication event sequence is missing, duplicated, or reordered");
            Message message = declared.get(event.messageId());
            require(message != null && message.recipient().equals(event.actor()),
                "Event has no matching delivered recipient");
            boolean recorded = switch (event.stage()) {
                case DELIVERED -> journal.delivered(message);
                case READ -> journal.read(event.messageId(), event.actor(), event.decisionId(), event.tick());
                case SELECTED -> journal.selected(event.messageId(), event.actor(), event.decisionId(), event.tick());
                case ASSIGNED -> journal.assigned(event.messageId(), event.actor(), event.decisionId(), event.jobId(), event.tick());
                case PHYSICAL_COMPLETED -> journal.completed(event.jobId(), event.actor(), event.tick());
            };
            require(recorded && journal.events.size() == sequence
                && journal.events.get(journal.events.size() - 1).equals(event),
                "Restored event conflicts with its lifecycle or sequence");
        }
        require(journal.messages.size() == declared.size(), "Message is missing its delivery event");
        journal.capacityDenials = capacityDenials;
        return journal;
    }

    private Message recipientMessage(UUID messageId, UUID recipient) {
        require(messageId != null && recipient != null, "Missing message or recipient");
        Message message = messages.get(messageId);
        require(message != null && message.recipient().equals(recipient),
            "Unknown report or counterfeit recipient");
        return message;
    }

    private void checkDecisionScope(Message message, UUID decision) {
        DecisionScope previous = decisionScopes.get(decision);
        require(previous == null || previous.equals(scope(message)),
            "Decision identity cannot cross recipients, worlds, or episodes");
    }

    private boolean replay(Event previous, Message message, UUID actor,
                           UUID decision, UUID job, long tick) {
        require(previous.messageId().equals(message.id()) && previous.actor().equals(actor)
            && java.util.Objects.equals(previous.decisionId(), decision)
            && java.util.Objects.equals(previous.jobId(), job) && previous.tick() == tick,
            "Conflicting communication event replay");
        return true;
    }

    private Event next(Stage stage, Message message, UUID decision, UUID job, long tick) {
        return new Event(events.size() + 1L, stage, message.id(), message.recipient(), decision, job, tick);
    }

    private boolean denied() {
        if (capacityDenials != Long.MAX_VALUE) capacityDenials++;
        return false;
    }

    private static DeliveryKey deliveryKey(Message message) {
        return new DeliveryKey(message.world(), message.episode(), message.recipient(), message.reportId());
    }

    private static DecisionScope scope(Message message) {
        return new DecisionScope(message.recipient(), message.world(), message.episode());
    }

    private static boolean text(String value) {
        return value != null && !value.isBlank() && value.length() <= 4096;
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }
}
