package dev.hearthbound.learning;

import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class VerifiedRewardReplaySavedDataTest {
    static VerifiedTrainingTransitions.Transition record(UUID job, String evidence) {
        return new VerifiedTrainingTransitions.Transition(1, job, UUID.randomUUID(),
                10L, 23L, "PROPOSE", "create:milling/wheat", evidence,
                new OutcomeLedger.RewardVector(0.5, 0.8, 1.0));
    }

    @Test void roundTripRetainsVerifiedRewards() {
        var replay = VerifiedRewardReplaySavedData.load(new CompoundTag());
        var item = record(UUID.randomUUID(), "create:millstone:job-1");
        assertTrue(replay.append(item));
        assertFalse(replay.append(item));
        var saved = replay.save(new CompoundTag());
        var restored = VerifiedRewardReplaySavedData.load(saved);
        assertEquals(item, restored.snapshot().get(item.job()));
    }

    @Test void rejectsConflictingJobAndRepeatedEvidence() {
        var replay = VerifiedRewardReplaySavedData.load(new CompoundTag());
        var first = record(UUID.randomUUID(), "receipt-A");
        replay.append(first);
        assertThrows(IllegalStateException.class, () ->
            replay.append(record(first.job(), "receipt-B")));
        assertThrows(IllegalStateException.class, () ->
            replay.append(record(UUID.randomUUID(), "receipt-A")));
        assertEquals(1, replay.snapshot().size());
    }

    @Test void rejectsUnverifiedShape() {
        var replay = VerifiedRewardReplaySavedData.load(new CompoundTag());
        var invalid = new VerifiedTrainingTransitions.Transition(1, UUID.randomUUID(),
                UUID.randomUUID(), 50, 49, "DEFER", "", "",
                new OutcomeLedger.RewardVector(0, 0, 0));
        assertThrows(IllegalArgumentException.class, () -> replay.append(invalid));
    }
}
