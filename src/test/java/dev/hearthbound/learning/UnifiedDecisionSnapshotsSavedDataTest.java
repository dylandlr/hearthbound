package dev.hearthbound.learning;

import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class UnifiedDecisionSnapshotsSavedDataTest {
    private static UnifiedCitizenObservation.Snapshot sample(UUID citizen) {
        double[] c=new double[CitizenLocalStateSensor.WIDTH];
        double[] r=new double[ResearchObservationVector.WIDTH];
        c[0]=.8; r[0]=.6;
        return new UnifiedCitizenObservation.Snapshot(1,citizen,14,1,c,1,r);
    }
    @Test void saveRestorePreservesBothDomains() {
        var data=UnifiedDecisionSnapshotsSavedData.load(new CompoundTag());
        UUID citizen=UUID.randomUUID(), job=UUID.randomUUID();
        data.record(job,sample(citizen));
        var restored=UnifiedDecisionSnapshotsSavedData.load(data.save(new CompoundTag()));
        assertEquals(citizen,restored.require(job).citizen());
        assertEquals(14,restored.require(job).gameTick());
        assertEquals(.8,restored.require(job).citizenFeatures()[0]);
        assertEquals(.6,restored.require(job).researchFeatures()[0]);
        restored.record(job,sample(citizen));
        assertThrows(IllegalStateException.class,
                () -> restored.record(job,sample(UUID.randomUUID())));
    }
    @Test void absentResearchDomainIsNotFilledWithZeros() {
        var data=UnifiedDecisionSnapshotsSavedData.load(new CompoundTag());
        UUID job=UUID.randomUUID();
        var snapshot=new UnifiedCitizenObservation.Snapshot(
                1,UUID.randomUUID(),9,1,new double[10],0,null);
        data.record(job,snapshot);
        var restored=UnifiedDecisionSnapshotsSavedData.load(data.save(new CompoundTag()));
        assertFalse(restored.require(job).hasResearchContext());
        assertThrows(IllegalStateException.class,
                () -> restored.require(job).flatForResearchModel());
    }
}
