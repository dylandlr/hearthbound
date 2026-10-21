package dev.hearthbound.learning;

import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ResearchSuccessorObservationsSavedDataTest {
    @Test void observedRoundTripAndDefensiveCopy() {
        var data = ResearchSuccessorObservationsSavedData.load(new CompoundTag());
        var job=UUID.randomUUID(); var citizen=UUID.randomUUID();
        double[] raw=new double[ResearchObservationVector.WIDTH];
        raw[0]=.64;
        var sample=new ResearchSuccessorObservationsSavedData.Successor(job,citizen,30,
                ResearchSuccessorObservationsSavedData.Status.OBSERVED,raw);
        data.record(sample);
        raw[0]=0;
        var restored=ResearchSuccessorObservationsSavedData.load(data.save(new CompoundTag()));
        assertEquals(sample,restored.require(job));
        double[] exposed=restored.require(job).features();
        exposed[0]=0;
        assertEquals(.64,restored.require(job).features()[0]);
        restored.record(sample);
    }
    @Test void unavailableIsNotZeroState() {
        var data=ResearchSuccessorObservationsSavedData.load(new CompoundTag());
        var job=UUID.randomUUID(); var citizen=UUID.randomUUID();
        var unavailable=new ResearchSuccessorObservationsSavedData.Successor(job,citizen,31,
                ResearchSuccessorObservationsSavedData.Status.UNAVAILABLE,null);
        data.record(unavailable);
        var restored=ResearchSuccessorObservationsSavedData.load(data.save(new CompoundTag()));
        assertEquals(ResearchSuccessorObservationsSavedData.Status.UNAVAILABLE,restored.require(job).status());
        assertNull(restored.require(job).features());
        assertThrows(IllegalStateException.class,()->restored.record(
                new ResearchSuccessorObservationsSavedData.Successor(job,citizen,32,
                ResearchSuccessorObservationsSavedData.Status.UNAVAILABLE,null)));
        assertThrows(IllegalArgumentException.class,()->new ResearchSuccessorObservationsSavedData.Successor(
                UUID.randomUUID(),citizen,32,
                ResearchSuccessorObservationsSavedData.Status.UNAVAILABLE,new double[11]));
    }
}
