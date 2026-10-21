package dev.hearthbound.learning;

import dev.hearthbound.research.MillResearchRewards;
import dev.hearthbound.research.ResearchDecisionTraceJournal;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * Training-data assembler only. No policy updates, evidence minting, or world mutations.
 * A binding must be made when the physical job is assigned; a later verified award
 * closes the binding exactly once.
 */
public final class VerifiedTrainingTransitions {
    public record Binding(UUID job, UUID citizen, ResearchDecisionTraceJournal.Trace decision) {
        public Binding {
            Objects.requireNonNull(job, "job");
            Objects.requireNonNull(citizen, "citizen");
            Objects.requireNonNull(decision, "decision");
            if (!citizen.toString().equals(decision.citizenId()))
                throw new IllegalArgumentException("decision citizen differs from job citizen");
            if (!"PROPOSE".equals(decision.personality().action()))
                throw new IllegalArgumentException("training action must be executed policy proposal");
        }
    }
    public record Transition(int schemaVersion, UUID job, UUID citizen, long decisionTick,
            long outcomeTick, String action, String recipeId, String evidenceId,
            OutcomeLedger.RewardVector reward) {}

    private final Map<UUID, Binding> pending = new LinkedHashMap<>();
    private final Map<UUID, Transition> complete = new LinkedHashMap<>();
    private final Map<String, UUID> evidenceOwners = new LinkedHashMap<>();

    public synchronized void bind(Binding binding) {
        Objects.requireNonNull(binding, "binding");
        if (complete.containsKey(binding.job())) throw new IllegalStateException("job already finalized");
        Binding existing = pending.putIfAbsent(binding.job(), binding);
        if (existing != null && !existing.equals(binding))
            throw new IllegalStateException("job already bound to different decision");
    }

    /** Must receive awardVerified() output, never a predicted or proposed outcome. */
    public synchronized Transition finalizeVerified(MillResearchRewards.Award award) {
        Objects.requireNonNull(award, "award");
        if (complete.containsKey(award.job())) throw new IllegalStateException("award already finalized");
        Binding binding = pending.get(award.job());
        if (binding == null) throw new IllegalStateException("missing physical-job decision binding");
        if (!binding.citizen().equals(award.citizen())) throw new IllegalArgumentException("wrong citizen");
        if (binding.decision().gameTick() > award.tick()) throw new IllegalArgumentException("future decision");
        if (award.evidenceId() == null || award.evidenceId().isBlank())
            throw new IllegalArgumentException("missing receipt evidence");
        if (evidenceOwners.containsKey(award.evidenceId()))
            throw new IllegalStateException("physical evidence already finalized");
        var d = binding.decision().personality();
        Transition result = new Transition(1, award.job(), award.citizen(), binding.decision().gameTick(),
                award.tick(), d.action(), d.recipeId(), award.evidenceId(), award.reward());
        complete.put(award.job(), result);
        evidenceOwners.put(award.evidenceId(), award.job());
        pending.remove(award.job());
        return result;
    }

    public synchronized Map<UUID, Transition> snapshot() {
        return Map.copyOf(complete);
    }
    public synchronized int pendingCount() { return pending.size(); }
}
