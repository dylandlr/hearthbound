package dev.hearthbound.learning;

import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ResearchObservationSnapshotsSavedDataTest {
    @Test void worldSaveRoundTripKeepsExactOriginalObservation() {
        var data = ResearchObservationSnapshotsSavedData.load(new CompoundTag());
        UUID job = UUID.randomUUID(), citizen = UUID.randomUUID();
        double[] values = new double[ResearchObservationVector.WIDTH];
        values[0] = .72; values[3] = 1; values[4] = .8;
        var original = new ResearchObservationSnapshotsSavedData.Snapshot(job,citizen,17,values);
        data.add(original);
        values[0] = 0;
        assertEquals(.72,data.require(job).features()[0]);
        var restored = ResearchObservationSnapshotsSavedData.load(data.save(new CompoundTag()));
        assertEquals(original,restored.require(job));
        double[] leaked = restored.require(job).features();
        leaked[0] = 0;
        assertEquals(.72,restored.require(job).features()[0]);
    }

    @Test void duplicatedJobCannotChangeStoredHistory() {
        var data = ResearchObservationSnapshotsSavedData.load(new CompoundTag());
        UUID job = UUID.randomUUID(), citizen = UUID.randomUUID();
        var first = new ResearchObservationSnapshotsSavedData.Snapshot(
                job,citizen,9,new double[ResearchObservationVector.WIDTH]);
        data.add(first);
        data.add(first);
        assertEquals(1,data.size());
        assertThrows(IllegalStateException.class, () -> data.add(
                new ResearchObservationSnapshotsSavedData.Snapshot(
                        job,citizen,10,new double[ResearchObservationVector.WIDTH])));
    }

    @Test void invalidWidthOrValuesAreRejected() {
        UUID job=UUID.randomUUID(),citizen=UUID.randomUUID();
        assertThrows(IllegalArgumentException.class, () ->
                new ResearchObservationSnapshotsSavedData.Snapshot(job,citizen,1,new double[3]));
        var values = new double[ResearchObservationVector.WIDTH];
        values[2] = Double.NaN;
        assertThrows(IllegalArgumentException.class, () ->
                new ResearchObservationSnapshotsSavedData.Snapshot(job,citizen,1,values));
    }
}
