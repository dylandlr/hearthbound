package dev.hearthbound.research;
import static org.junit.jupiter.api.Assertions.*;
import java.util.List;
import org.junit.jupiter.api.Test;
class ExperimentSelectionPolicyTest {
    final ExperimentSelectionPolicy policy=new ExperimentSelectionPolicy();
    ExperimentSelectionPolicy.Candidate candidate(String id,boolean input,boolean machine,boolean falseBefore) {
        return new ExperimentSelectionPolicy.Candidate(id,"minecraft:wheat","create:millstone",
            "create:wheat_flour",.9,.15,input,machine,falseBefore);
    }
    @Test void picksLocallyObservableExperiment() {
        var o=new ExperimentSelectionPolicy.Observation(1,.8,.2,.1,
            List.of(candidate("experiment:invisible",false,true,false),
                    candidate("create:milling/wheat",true,true,false)));
        assertEquals("create:milling/wheat",policy.select(o).candidate().recipeId());
    }
    @Test void neverSelectsAbsentMachineOrFalsifiedHypothesis() {
        var o=new ExperimentSelectionPolicy.Observation(1,1,0,0,
            List.of(candidate("a",true,false,false),candidate("b",true,true,true)));
        assertEquals(ExperimentSelectionPolicy.Action.DEFER,policy.select(o).action());
    }
    @Test void exhaustionAndScarcityDiscourageExperiments() {
        var c=new ExperimentSelectionPolicy.Candidate("r","i","m","o",.1,1,true,true,false);
        assertEquals(ExperimentSelectionPolicy.Action.DEFER,policy.select(
            new ExperimentSelectionPolicy.Observation(1,.25,1,.8,List.of(c))).action());
    }
    @Test void schemaAndNonfiniteInputsRejected() {
        assertThrows(IllegalArgumentException.class,()->new ExperimentSelectionPolicy.Observation(
            2,0,0,0,List.of()));
        assertThrows(IllegalArgumentException.class,()->new ExperimentSelectionPolicy.Candidate(
            "r","i","m","o",Double.NaN,0,true,true,false));
    }
}
