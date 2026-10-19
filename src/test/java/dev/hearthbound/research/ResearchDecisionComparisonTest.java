package dev.hearthbound.research;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;
class ResearchDecisionComparisonTest {
    @Test void identicalObservationCanExposePersonalityDifference() {
        var candidate=new ExperimentSelectionPolicy.Candidate("wheat","wheat","millstone",
            "flour",0.1,0.8,true,true,false);
        var observation=new ExperimentSelectionPolicy.Observation(1,0.05,1,0.1,List.of(candidate));
        var pair=ResearchDecisionComparison.evaluate(observation);
        assertEquals(1,pair.schemaVersion());
        assertTrue(pair.disagree());
        assertEquals(ExperimentSelectionPolicy.Action.DEFER,pair.personality().choice().action());
        assertEquals(ExperimentSelectionPolicy.Action.PROPOSE,pair.scripted().choice().action());
    }
    @Test void noPhysicalCandidateMeansNoDecisionForEither() {
        var obs=new ExperimentSelectionPolicy.Observation(1,1,0,0,List.of());
        var pair=ResearchDecisionComparison.evaluate(obs);
        assertFalse(pair.disagree());
        assertEquals(ExperimentSelectionPolicy.Action.DEFER,pair.scripted().choice().action());
    }
}
