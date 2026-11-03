package dev.hearthbound.perception;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * Standalone Java 17 research primitive for event-driven, per-citizen
 * knowledge. No Forge hooks, inventory access, world scans or task dispatch.
 *
 * A server adapter (not implemented here) must authenticate subject access
 * before calling subscribe / observe. Reported beliefs and future machine
 * vision predictions are never authoritative server facts.
 */
public final class SharedPerceptionLedger {
    public enum Origin { SERVER_EVENT, DIRECT_OBSERVATION, CITIZEN_REPORT, VISION_PREDICTION }
    public enum Validity { CURRENT, EXPIRED, GAP, UNKNOWN }
    public record Fact(String subject, String property, String value,
                       Origin origin, String observer, long observedTick,
                       long sequence, int ttlTicks) {
        public Fact {
            if (subject == null || subject.isBlank() || property == null || property.isBlank()
                    || value == null || value.isBlank() || observer == null || observer.isBlank()
                    || origin == null || observedTick < 0 || sequence <= 0 || ttlTicks < 1)
                throw new IllegalArgumentException("Invalid perception fact");
        }
        public boolean authoritative() {
            return origin == Origin.SERVER_EVENT || origin == Origin.DIRECT_OBSERVATION;
        }
    }
    public record Known(Fact fact, Validity validity, long ageTicks) {
        public Known {
            Objects.requireNonNull(validity);
            if (ageTicks < 0) throw new IllegalArgumentException("Negative age");
        }
    }
    public record Delivery(long sequence, Fact fact, boolean gap) {}
    private static final class Inbox {
        final Set<String> subjects = new HashSet<>();
        final Deque<Delivery> queue = new ArrayDeque<>();
        final Map<String, Fact> knowledge = new HashMap<>();
        long lastSeq = 0;
        boolean gap = false;
    }
    private final Map<String, Inbox> inboxes = new HashMap<>();
    private final int maxQueue;
    private long tick;
    private long sequence;

    public SharedPerceptionLedger(int maxQueue, long initialTick) {
        if (maxQueue < 1 || initialTick < 0)
            throw new IllegalArgumentException("Invalid queue bound / tick");
        this.maxQueue = maxQueue;
        this.tick = initialTick;
    }
    public long tick() { return tick; }
    public void advance(long nextTick) {
        if (nextTick < tick) throw new IllegalArgumentException("World tick moved backwards");
        tick = nextTick;
    }
    /**
     * The caller is responsible for validating the subscription against
     * citizen location, job and access rules; no implicit global broadcast.
     */
    public void subscribe(String citizen, String subject) {
        Inbox i = inbox(citizen);
        if (subject == null || subject.isBlank())
            throw new IllegalArgumentException("Invalid subject");
        i.subjects.add(subject);
    }
    public void unsubscribe(String citizen, String subject) {
        Inbox i = inbox(citizen);
        i.subjects.remove(subject);
        i.knowledge.keySet().removeIf(k -> k.startsWith(subject + "\u0000"));
        i.queue.removeIf(d -> d.fact() != null && d.fact().subject().equals(subject));
    }
    /**
     * Publishing an event never claims the subject was actually inspected.
     * Server integration must validate and supply evidence at this boundary.
     */
    public Fact publish(String subject, String property, String value,
                        Origin origin, String observer, int ttl) {
        if (origin == null) throw new IllegalArgumentException("Missing origin");
        Fact fact = new Fact(subject, property, value, origin, observer,
                             tick, ++sequence, ttl);
        for (Inbox i : inboxes.values()) {
            if (!i.subjects.contains(subject)) continue;
            // Evidence is delivered only to explicitly subscribed citizens.
            if (i.queue.size() >= maxQueue) {
                i.queue.removeFirst();
                i.gap = true;
            }
            i.queue.addLast(new Delivery(fact.sequence(), fact, false));
        }
        return fact;
    }
    /**
     * A bounded mailbox. A dropped update marks future cache reads UNKNOWN
     * until a new authoritative observation is delivered for that key.
     */
    public List<Delivery> drain(String citizen) {
        Inbox i = inbox(citizen);
        List<Delivery> out = new ArrayList<>();
        if (i.gap) {
            i.knowledge.clear();
            out.add(new Delivery(++sequence, null, true));
            i.gap = false;
        }
        while (!i.queue.isEmpty()) {
            Delivery d = i.queue.removeFirst();
            out.add(d);
            Fact f = d.fact();
            String key = key(f.subject(), f.property());
            Fact prior = i.knowledge.get(key);
            // A second-hand claim or vision guess cannot overwrite a
            // server-verified or directly observed fact.
            if (prior != null && prior.authoritative() && !f.authoritative())
                continue;
            if (prior == null || f.sequence() > prior.sequence())
                i.knowledge.put(key, f);
            i.lastSeq = Math.max(i.lastSeq, f.sequence());
        }
        return List.copyOf(out);
    }
    public Known read(String citizen, String subject, String property) {
        Inbox i = inbox(citizen);
        if (!i.subjects.contains(subject))
            return new Known(null, Validity.UNKNOWN, 0);
        Fact fact = i.knowledge.get(key(subject, property));
        if (fact == null) return new Known(null, Validity.UNKNOWN, 0);
        long age = tick - fact.observedTick();
        if (age < 0) throw new IllegalStateException("Future perception evidence");
        if (i.gap) return new Known(null, Validity.GAP, age);
        return new Known(fact, age <= fact.ttlTicks()
                        ? Validity.CURRENT : Validity.EXPIRED, age);
    }
    public int pending(String citizen) { return inbox(citizen).queue.size(); }
    private static String key(String subject, String property) {
        return subject + "\u0000" + property;
    }
    private Inbox inbox(String citizen) {
        if (citizen == null || citizen.isBlank())
            throw new IllegalArgumentException("Invalid citizen");
        return inboxes.computeIfAbsent(citizen, k -> new Inbox());
    }
}
