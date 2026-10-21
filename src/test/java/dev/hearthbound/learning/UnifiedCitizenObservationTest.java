package dev.hearthbound.learning;

import dev.hearthbound.research.ExperimentSelectionPolicy;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class UnifiedCitizenObservationTest {
    private CitizenLocalStateSensor.Snapshot state() {
        var values=new double[CitizenLocalStateSensor.WIDTH];
        values[0]=.8;
        return new CitizenLocalStateSensor.Snapshot(1,values);
    }

    @Test void missingResearchIsExplicitAndCannotBeFlattened() {
        var snapshot=UnifiedCitizenObservation.combine(UUID.randomUUID(),12,state(),null);
        assertFalse(snapshot.hasResearchContext());
        assertNull(snapshot.researchFeatures());
        assertThrows(IllegalStateException.class,snapshot::flatForResearchModel);
    }

    @Test void domainsKeepDistinctVersionsAndDefensiveCopies() {
        var research=ResearchObservationVector.from(new ExperimentSelectionPolicy.Observation(
                1,.7,.2,.1,List.of()));
        var snapshot=UnifiedCitizenObservation.combine(UUID.randomUUID(),12,state(),research);
        assertTrue(snapshot.hasResearchContext());
        assertEquals(21,snapshot.flatForResearchModel().length);
        assertEquals(.8,snapshot.citizenFeatures()[0]);
        assertEquals(.7,snapshot.flatForResearchModel()[10]);
        var leaked=snapshot.flatForResearchModel();
        leaked[0]=999;
        assertEquals(.8,snapshot.citizenFeatures()[0]);
        assertThrows(IllegalArgumentException.class,()->new UnifiedCitizenObservation.Snapshot(
                1,UUID.randomUUID(),12,99,state().features(),1,research.values()));
    }
}
