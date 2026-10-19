package dev.hearthbound.research;
import static org.junit.jupiter.api.Assertions.*;
import java.util.List;
import org.junit.jupiter.api.Test;
class ResearchPolicyBaselinesTest {
    @Test void sameObservationGivesSameScriptedDecision() {
        var c=new ExperimentSelectionPolicy.Candidate("create:milling/wheat","minecraft:wheat",
            "create:millstone","create:wheat_flour",.8,.2,true,true,false);
        var low=new ExperimentSelectionPolicy.Observation(1,0,.5,0,List.of(c));
        var high=new ExperimentSelectionPolicy.Observation(1,1,.5,0,List.of(c));
        assertEquals(ResearchPolicyBaselines.choose(ResearchPolicyBaselines.Mode.SCRIPTED,low).choice(),
                     ResearchPolicyBaselines.choose(ResearchPolicyBaselines.Mode.SCRIPTED,high).choice());
        assertNotEquals(ResearchPolicyBaselines.choose(ResearchPolicyBaselines.Mode.PERSONALITY,low).choice(),
                        ResearchPolicyBaselines.choose(ResearchPolicyBaselines.Mode.PERSONALITY,high).choice());
    }
    @Test void missingPhysicalPrerequisitesCannotBeOverriddenByEitherPolicy() {
        var c=new ExperimentSelectionPolicy.Candidate("r","wheat","mill","flour",1,0,false,true,false);
        var o=new ExperimentSelectionPolicy.Observation(1,1,0,0,List.of(c));
        for(var m:ResearchPolicyBaselines.Mode.values())
            assertEquals(ExperimentSelectionPolicy.Action.DEFER,ResearchPolicyBaselines.choose(m,o).choice().action());
    }
}
