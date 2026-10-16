package dev.hearthbound.research;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

final class LearningDecisionPolicyTest {
    private final LearningDecisionPolicy baseline = new LearningDecisionPolicy();

    @Test void hungryCitizenPrioritizesRecovery() {
        var o = new LearningDecisionPolicy.Observation(1,.9,.9,.2,1,.8,0,0,
                true,true,true,true);
        assertEquals(LearningDecisionPolicy.Action.REST, baseline.select(o).action());
    }
    @Test void accessibleBookMakesStudyPossible() {
        var o = new LearningDecisionPolicy.Observation(1,1,1,0,0,0,0,0,
                true,false,false,false);
        assertEquals(LearningDecisionPolicy.Action.OBSERVE_BOOK,baseline.select(o).action());
    }
    @Test void hiddenBookCannotBeChosen() {
        var o = new LearningDecisionPolicy.Observation(1,1,1,0,0,0,0,0,
                false,false,false,false);
        assertNotEquals(LearningDecisionPolicy.Action.OBSERVE_BOOK, baseline.select(o).action());
    }
    @Test void productionCanWinWhenCompetentAndUrgent() {
        var o = new LearningDecisionPolicy.Observation(1,.1,.1,0,0,1,1,1,
                true,false,false,true);
        assertEquals(LearningDecisionPolicy.Action.EXPLOIT, baseline.select(o).action());
    }
    @Test void rejectInvalidObservations() {
        assertThrows(IllegalArgumentException.class, () ->
                new LearningDecisionPolicy.Observation(2,.1,.1,0,0,0,0,0,
                        false,false,false,false));
    }
}
