package dev.hearthbound.learning;

import dev.hearthbound.research.ExperimentSelectionPolicy;
import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ResearchObservationVectorTest {
    private static ExperimentSelectionPolicy.Candidate candidate(String id) {
        return new ExperimentSelectionPolicy.Candidate(
                id, "minecraft:wheat", "create:millstone", "create:wheat_flour",
                .8, .2, true, true, false);
    }

    @Test void deterministicFeatureOrderAndBounds() {
        var observation = new ExperimentSelectionPolicy.Observation(1,.75,.5,.1,
                List.of(candidate("z"), candidate("a")));
        var vector = ResearchObservationVector.from(observation);
        assertEquals(11, vector.values().length);
        assertEquals(.75, vector.value(0));
        assertEquals(1, vector.value(3));
        assertEquals(.125, vector.value(9));
        assertEquals(.125, vector.value(10));
        assertEquals(vector, ResearchObservationVector.from(
                new ExperimentSelectionPolicy.Observation(1,.75,.5,.1,
                        List.of(candidate("a"),candidate("z")))));
    }

    @Test void noCandidateUsesPresenceMaskRatherThanInventingInputs() {
        var vector = ResearchObservationVector.from(new ExperimentSelectionPolicy.Observation(
                1,.3,.4,.5,List.of()));
        assertEquals(0,vector.value(3));
        for (int i=4; i<ResearchObservationVector.WIDTH;i++) assertEquals(0,vector.value(i));
    }

    @Test void defensiveCopiesPreventTrainingMutation() {
        var vector = ResearchObservationVector.from(new ExperimentSelectionPolicy.Observation(
                1,.3,.4,.5,List.of(candidate("wheat"))));
        var values=vector.values();
        values[0]=999;
        assertEquals(.3, vector.value(0));
        assertThrows(IllegalArgumentException.class,()->ResearchObservationVector.from(null));
    }
}
