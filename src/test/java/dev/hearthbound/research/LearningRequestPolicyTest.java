package dev.hearthbound.research;
import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;
class LearningRequestPolicyTest {
    final LearningRequestPolicy policy = new LearningRequestPolicy();
    @Test void interestedUninformedCitizenRequests() {
        assertEquals(LearningRequestPolicy.Action.REQUEST,policy.select(
            new LearningRequestPolicy.Observation(1,.8,0,.8,false,true,false)));
    }
    @Test void hiddenTeacherAndKnownRecipeNeverTrigger() {
        assertEquals(LearningRequestPolicy.Action.DEFER,policy.select(
            new LearningRequestPolicy.Observation(1,1,0,1,false,false,false)));
        assertEquals(LearningRequestPolicy.Action.DEFER,policy.select(
            new LearningRequestPolicy.Observation(1,1,1,1,true,true,false)));
    }
    @Test void repeatedRequestAndReluctantStudentDefer() {
        assertEquals(LearningRequestPolicy.Action.DEFER,policy.select(
            new LearningRequestPolicy.Observation(1,1,0,1,false,true,true)));
        assertEquals(LearningRequestPolicy.Action.DEFER,policy.select(
            new LearningRequestPolicy.Observation(1,0,0,0,false,true,false)));
    }
    @Test void rejectsBadSchemaAndNaN() {
        assertThrows(IllegalArgumentException.class,()->new LearningRequestPolicy.Observation(
            2,0,0,0,false,false,false));
        assertThrows(IllegalArgumentException.class,()->new LearningRequestPolicy.Observation(
            1,Double.NaN,0,0,false,false,false));
    }
}
