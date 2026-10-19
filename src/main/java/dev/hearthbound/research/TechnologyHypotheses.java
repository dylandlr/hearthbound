package dev.hearthbound.research;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/**
 * LLM-free, per-agent hypotheses of physical recipes.
 * A conjecture is never an unlock. Only a journaled, server-verified outcome
 * can confirm it, and a failed experiment never counts as physical proof.
 */
public final class TechnologyHypotheses {
    public enum Status { PROPOSED, FALSIFIED, CONFIRMED }
    public record Hypothesis(String agentId, String recipeId, String inputItem,
                             String machineType, String expectedOutput, Status status,
                             String evidenceId) {}
    private final Map<String, Hypothesis> hypotheses = new LinkedHashMap<>();
    private static String key(String agent, String recipe) { return agent + "\u0000" + recipe; }
    private static void nonblank(String v) {
        if (v == null || v.isBlank()) throw new IllegalArgumentException("Empty hypothesis field");
    }
    public synchronized Hypothesis propose(String agent, String recipe, String input,
                                           String machine, String output) {
        for (String value : new String[]{agent,recipe,input,machine,output}) nonblank(value);
        String id=key(agent,recipe);
        Hypothesis proposal = new Hypothesis(agent,recipe,input,machine,output,Status.PROPOSED,null);
        Hypothesis previous = hypotheses.putIfAbsent(id,proposal);
        if (previous != null && (!previous.inputItem().equals(input)
                || !previous.machineType().equals(machine)
                || !previous.expectedOutput().equals(output)))
            throw new IllegalStateException("Conflicting proposal; make a separate recipe hypothesis");
        return previous == null ? proposal : previous;
    }
    public synchronized Hypothesis observe(String agent, String recipe,
                                          String evidenceId, WorldEvidenceJournal journal) {
        nonblank(agent); nonblank(recipe); nonblank(evidenceId);
        Objects.requireNonNull(journal);
        String id=key(agent,recipe);
        Hypothesis prior=hypotheses.get(id);
        if (prior == null) throw new IllegalArgumentException("Unknown hypothesis");
        WorldEvidenceJournal.ProcessingEvidence proof=journal.require(evidenceId);
        if (!proof.physicallyVerified() || !proof.recipeId().equals(recipe))
            throw new IllegalArgumentException("Unverified or unrelated evidence");
        boolean matches = proof.inputItem().equals(prior.inputItem())
                && proof.machineType().equals(prior.machineType())
                && proof.outputItem().equals(prior.expectedOutput());
        if (prior.status()==Status.CONFIRMED) {
            if (!Objects.equals(prior.evidenceId(), evidenceId))
                throw new IllegalStateException("Already confirmed using different evidence");
            return prior;
        }
        Hypothesis updated = new Hypothesis(agent,recipe,prior.inputItem(),prior.machineType(),
                prior.expectedOutput(),matches?Status.CONFIRMED:Status.FALSIFIED,evidenceId);
        hypotheses.put(id,updated);
        return updated;
    }
    /** Stable records for world-save persistence and deterministic replay. */
    public synchronized java.util.List<Hypothesis> snapshot() {
        return java.util.List.copyOf(hypotheses.values());
    }

    /** Restore only validated records. Corrupt or conflicting saves fail closed. */
    public synchronized void restore(java.util.List<Hypothesis> saved) {
        Objects.requireNonNull(saved, "saved");
        Map<String,Hypothesis> validated = new LinkedHashMap<>();
        for (Hypothesis h : saved) {
            Objects.requireNonNull(h, "hypothesis");
            for (String field : new String[]{h.agentId(), h.recipeId(), h.inputItem(),
                    h.machineType(), h.expectedOutput()}) nonblank(field);
            Objects.requireNonNull(h.status(), "status");
            if (h.status() == Status.PROPOSED && h.evidenceId() != null)
                throw new IllegalArgumentException("Proposal cannot contain evidence");
            if (h.status() != Status.PROPOSED) nonblank(h.evidenceId());
            if (validated.putIfAbsent(key(h.agentId(),h.recipeId()),h) != null)
                throw new IllegalArgumentException("Duplicate persisted hypothesis");
        }
        hypotheses.clear();
        hypotheses.putAll(validated);
    }

    public synchronized Hypothesis require(String agent,String recipe) {
        Hypothesis h=hypotheses.get(key(agent,recipe));
        if(h==null) throw new IllegalArgumentException("Unknown hypothesis");
        return h;
    }
}
