package dev.hearthbound.research;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;

/**
 * Bounded, read-only-exportable per-citizen diagnostics.
 * Records policy decisions, not physical outcomes or training rewards.
 * Mutations are synchronized; exported snapshots are detached immutable values.
 */
public final class ResearchDecisionTraceJournal {
    public static final int SCHEMA_VERSION = 1;
    public record PolicyDecision(String action, String recipeId, double utility) {
        public PolicyDecision {
            Objects.requireNonNull(action, "action");
            if (!Double.isFinite(utility)) throw new IllegalArgumentException("non-finite utility");
        }
    }
    public record Trace(int schemaVersion, String citizenId, long gameTick,
                        PolicyDecision scripted, PolicyDecision personality,
                        boolean disagreement, String explanation) {
        public Trace {
            if (schemaVersion != SCHEMA_VERSION) throw new IllegalArgumentException("schema");
            if (citizenId == null || citizenId.isBlank()) throw new IllegalArgumentException("citizen");
            if (gameTick < 0) throw new IllegalArgumentException("tick");
            Objects.requireNonNull(scripted, "scripted");
            Objects.requireNonNull(personality, "personality");
            Objects.requireNonNull(explanation, "explanation");
        }
    }

    private final int capacityPerCitizen;
    private final Map<String, Deque<Trace>> traces = new TreeMap<>();
    private final Map<String, Long> latestTick = new TreeMap<>();

    public ResearchDecisionTraceJournal(int capacityPerCitizen) {
        if (capacityPerCitizen < 1 || capacityPerCitizen > 10_000)
            throw new IllegalArgumentException("capacity must be 1..10000");
        this.capacityPerCitizen = capacityPerCitizen;
    }

    public synchronized void record(String citizenId, long gameTick,
                                    ResearchDecisionComparison.Comparison comparison) {
        Objects.requireNonNull(comparison, "comparison");
        var s = comparison.scripted().choice();
        var p = comparison.personality().choice();
        Trace trace = new Trace(SCHEMA_VERSION, citizenId, gameTick,
                new PolicyDecision(s.action().name(),
                        s.candidate() == null ? null : s.candidate().recipeId(), s.utility()),
                new PolicyDecision(p.action().name(),
                        p.candidate() == null ? null : p.candidate().recipeId(), p.utility()),
                comparison.disagree(), comparison.explanation());
        append(trace);
    }

    /** Strictly increasing ticks prevent accidental duplicate decisions within a citizen stream. */
    public synchronized void append(Trace trace) {
        Objects.requireNonNull(trace, "trace");
        Long previous = latestTick.get(trace.citizenId());
        if (previous != null && trace.gameTick() <= previous)
            throw new IllegalArgumentException("duplicate or out-of-order tick");
        Deque<Trace> citizen = traces.computeIfAbsent(trace.citizenId(), ignored -> new ArrayDeque<>());
        citizen.addLast(trace);
        while (citizen.size() > capacityPerCitizen) citizen.removeFirst();
        latestTick.put(trace.citizenId(), trace.gameTick());
    }

    public synchronized List<Trace> snapshot(String citizenId) {
        return List.copyOf(traces.getOrDefault(citizenId, new ArrayDeque<>()));
    }

    public synchronized Map<String, List<Trace>> snapshotAll() {
        Map<String, List<Trace>> copy = new LinkedHashMap<>();
        traces.forEach((id, entries) -> copy.put(id, List.copyOf(entries)));
        return Map.copyOf(copy);
    }

    /** Portable JSON without external libraries; never includes world mutation or claimed outcomes. */
    public synchronized String exportJson() {
        StringBuilder out = new StringBuilder("{\"schemaVersion\":1,\"citizens\":[");
        boolean firstCitizen = true;
        for (var entry : traces.entrySet()) {
            if (!firstCitizen) out.append(',');
            firstCitizen = false;
            out.append("{\"citizenId\":").append(quote(entry.getKey())).append(",\"decisions\":[");
            boolean first = true;
            for (Trace trace : entry.getValue()) {
                if (!first) out.append(',');
                first = false;
                out.append("{\"gameTick\":").append(trace.gameTick())
                   .append(",\"scripted\":").append(policyJson(trace.scripted()))
                   .append(",\"personality\":").append(policyJson(trace.personality()))
                   .append(",\"disagreement\":").append(trace.disagreement())
                   .append(",\"explanation\":").append(quote(trace.explanation())).append('}');
            }
            out.append("]}");
        }
        return out.append("]}").toString();
    }

    private static String policyJson(PolicyDecision p) {
        return "{\"action\":" + quote(p.action()) + ",\"recipeId\":" +
                (p.recipeId() == null ? "null" : quote(p.recipeId())) +
                ",\"utility\":" + Double.toString(p.utility()) + "}";
    }

    private static String quote(String value) {
        StringBuilder out = new StringBuilder("\"");
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                default -> {
                    if (c < 32) out.append(String.format("\\u%04x", (int)c));
                    else out.append(c);
                }
            }
        }
        return out.append('"').toString();
    }
}
