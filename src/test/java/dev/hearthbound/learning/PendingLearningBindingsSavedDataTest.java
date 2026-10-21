package dev.hearthbound.learning;

import dev.hearthbound.research.ResearchDecisionTraceJournal;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class PendingLearningBindingsSavedDataTest {
    static VerifiedTrainingTransitions.Binding binding(UUID job, UUID citizen) {
        var scripted = new ResearchDecisionTraceJournal.PolicyDecision("DEFER", null, 0.1);
        var personality = new ResearchDecisionTraceJournal.PolicyDecision(
                "PROPOSE", "create:milling/wheat", 0.8);
        var trace = new ResearchDecisionTraceJournal.Trace(1, citizen.toString(), 42L,
                scripted, personality, true, "curiosity");
        return new VerifiedTrainingTransitions.Binding(job, citizen, trace);
    }

    @Test void restartRoundTripPreservesDecisionAttribution() {
        var before = PendingLearningBindingsSavedData.load(new CompoundTag());
        UUID job=UUID.randomUUID(), citizen=UUID.randomUUID();
        var entry=binding(job,citizen);
        before.add(entry);
        var after=PendingLearningBindingsSavedData.load(before.save(new CompoundTag()));
        assertEquals(entry, after.require(job));
        assertEquals(1, after.size());
        after.complete(job);
        assertEquals(0, PendingLearningBindingsSavedData.load(after.save(new CompoundTag())).size());
    }

    @Test void duplicateBindingIsIdempotentButConflictRejected() {
        var data = PendingLearningBindingsSavedData.load(new CompoundTag());
        UUID job=UUID.randomUUID(), citizen=UUID.randomUUID();
        data.add(binding(job,citizen));
        data.add(binding(job,citizen));
        assertEquals(1,data.size());
        assertThrows(IllegalStateException.class,
                () -> data.add(binding(job,UUID.randomUUID())));
        assertThrows(IllegalStateException.class,
                () -> data.require(UUID.randomUUID()));
    }

    @Test void malformedBindingsAreRejected() {
        var data = PendingLearningBindingsSavedData.load(new CompoundTag());
        var citizen=UUID.randomUUID();
        var trace = new ResearchDecisionTraceJournal.Trace(1, citizen.toString(), 4,
                new ResearchDecisionTraceJournal.PolicyDecision("DEFER",null,0),
                new ResearchDecisionTraceJournal.PolicyDecision("PROPOSE",null,0),true,"bad");
        assertThrows(IllegalArgumentException.class,()->data.add(
                new VerifiedTrainingTransitions.Binding(UUID.randomUUID(),citizen,trace)));
    }
}
