package dev.hearthbound.learning;

import dev.hearthbound.research.ExperimentSelectionPolicy;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ResearchExperienceTransitionTest {
    private ResearchObservationVector observation(double curiosity) {
        return ResearchObservationVector.from(
                new ExperimentSelectionPolicy.Observation(1,curiosity,0.2,0.1,List.of()));
    }
    @Test void completeOnlyWithMeasuredSuccessor() {
        var reward = new VerifiedTrainingTransitions.Transition(1, UUID.randomUUID(),
                UUID.randomUUID(),10,30,"PROPOSE","create:milling/wheat","receipt",
                new OutcomeLedger.RewardVector(.5,.8,1));
        var transition = ResearchExperienceTransition.complete(
                reward,observation(.7),observation(.4),31,false);
        assertEquals(11,transition.state().length);
        assertEquals(.4,transition.nextState()[0]);
        assertEquals(1,transition.action());
        var exposed = transition.state();
        exposed[0] = 999;
        assertEquals(.7,transition.state()[0]);
        assertThrows(NullPointerException.class,()->ResearchExperienceTransition.complete(
                reward,observation(.7),null,31,false));
        assertThrows(IllegalArgumentException.class,()->ResearchExperienceTransition.complete(
                reward,observation(.7),observation(.4),29,false));
    }
}
