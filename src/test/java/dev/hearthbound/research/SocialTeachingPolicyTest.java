package dev.hearthbound.research;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

public class SocialTeachingPolicyTest {
    private final SocialTeachingPolicy policy = new SocialTeachingPolicy();

    @Test void cooperativeTrustedTeacherShares() {
        var o = new SocialTeachingPolicy.Observation(1, .9, .8, .8, .7, .1, true, true, false);
        assertEquals(SocialTeachingPolicy.Action.TEACH, policy.select(o).action());
    }
    @Test void noOmniscientTeachingToUnseenStudent() {
        var o = new SocialTeachingPolicy.Observation(1, 1, 1, 1, 1, 0, false, true, true);
        assertEquals(SocialTeachingPolicy.Action.DEFER, policy.select(o).action());
    }
    @Test void unknownRecipeCannotBeTaught() {
        var o = new SocialTeachingPolicy.Observation(1, 1, 1, 1, 1, 0, true, false, true);
        assertEquals(SocialTeachingPolicy.Action.DEFER, policy.select(o).action());
    }
    @Test void exhaustedCitizenRests() {
        var o = new SocialTeachingPolicy.Observation(1, 1, 1, 1, 1, .9, true, true, true);
        assertEquals(SocialTeachingPolicy.Action.REST, policy.select(o).action());
    }
    @Test void reluctantStrangerDefers() {
        var o = new SocialTeachingPolicy.Observation(1, .1, .4, 0, .1, .5, true, true, false);
        assertEquals(SocialTeachingPolicy.Action.DEFER, policy.select(o).action());
    }
    @Test void schemaRejectsBadOrNonfiniteValues() {
        assertThrows(IllegalArgumentException.class, () ->
                new SocialTeachingPolicy.Observation(2, 0, 0, 0, 0, 0, false, false, false));
        assertThrows(IllegalArgumentException.class, () ->
                new SocialTeachingPolicy.Observation(1, Double.NaN, 0, 0, 0, 0, false, false, false));
    }
}
