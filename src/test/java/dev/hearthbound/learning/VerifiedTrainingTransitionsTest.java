package dev.hearthbound.learning;

import dev.hearthbound.research.MillResearchRewards;
import dev.hearthbound.research.ResearchDecisionTraceJournal;
import java.util.UUID;
import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

class VerifiedTrainingTransitionsTest {
    private static ResearchDecisionTraceJournal.Trace trace(UUID citizen, long tick, String action) {
        return new ResearchDecisionTraceJournal.Trace(1, citizen.toString(), tick,
                new ResearchDecisionTraceJournal.PolicyDecision("PROPOSE", "create:milling/wheat", .7),
                new ResearchDecisionTraceJournal.PolicyDecision(action, "create:milling/wheat", .8),
                false, "local mill");
    }
    private static MillResearchRewards.Award award(UUID job, UUID citizen, long tick, String evidence) {
        return new MillResearchRewards.Award(job, citizen, 1L, tick,
                new OutcomeLedger.RewardVector(.5,.8,1), evidence);
    }
    @Test void verifiedAwardClosesBoundPhysicalJobOnce() {
        var journal = new VerifiedTrainingTransitions();
        UUID citizen=UUID.randomUUID(),job=UUID.randomUUID();
        journal.bind(new VerifiedTrainingTransitions.Binding(job,citizen,trace(citizen,10,"PROPOSE")));
        var result=journal.finalizeVerified(award(job,citizen,15,"receipt-1"));
        assertEquals(10,result.decisionTick());
        assertEquals("create:milling/wheat",result.recipeId());
        assertEquals(0,journal.pendingCount());
        assertEquals(1,journal.snapshot().size());
        assertThrows(IllegalStateException.class,()->journal.finalizeVerified(award(job,citizen,15,"receipt-1")));
    }
    @Test void invalidAttributionCannotCreateTrainingExamples() {
        var journal = new VerifiedTrainingTransitions();
        UUID citizen=UUID.randomUUID(),other=UUID.randomUUID(),job=UUID.randomUUID();
        assertThrows(IllegalArgumentException.class,()->new VerifiedTrainingTransitions.Binding(job,citizen,trace(other,1,"PROPOSE")));
        assertThrows(IllegalArgumentException.class,()->new VerifiedTrainingTransitions.Binding(job,citizen,trace(citizen,1,"DEFER")));
        journal.bind(new VerifiedTrainingTransitions.Binding(job,citizen,trace(citizen,10,"PROPOSE")));
        assertThrows(IllegalArgumentException.class,()->journal.finalizeVerified(award(job,other,11,"r")));
        assertThrows(IllegalArgumentException.class,()->journal.finalizeVerified(award(job,citizen,9,"r")));
        assertEquals(1,journal.pendingCount());
        assertEquals(0,journal.snapshot().size());
        journal.finalizeVerified(award(job,citizen,11,"r"));
        UUID second=UUID.randomUUID();
        journal.bind(new VerifiedTrainingTransitions.Binding(second,citizen,trace(citizen,12,"PROPOSE")));
        assertThrows(IllegalStateException.class,()->journal.finalizeVerified(award(second,citizen,13,"r")));
    }
}
