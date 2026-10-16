package dev.hearthbound.research;

import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

final class CitizenPriorityPolicyTest {
    private CitizenPriorityPolicy.Candidate c(CitizenPriorityPolicy.Job job, int priority, boolean available) {
        return new CitizenPriorityPolicy.Candidate(job,priority,0,0,0,0,available);
    }
    @Test void zeroTemperatureChoosesStrongestAllowedPriority() {
        var chosen=CitizenPriorityPolicy.choose(List.of(
                c(CitizenPriorityPolicy.Job.FARM,1,true),
                c(CitizenPriorityPolicy.Job.STUDY,3,true)),0,new Random(1));
        assertEquals(CitizenPriorityPolicy.Job.FARM,chosen.job());
    }
    @Test void cannotSelectUnavailableOrDisabledJobs() {
        var chosen=CitizenPriorityPolicy.choose(List.of(
                c(CitizenPriorityPolicy.Job.FARM,1,false),
                c(CitizenPriorityPolicy.Job.STUDY,0,true),
                c(CitizenPriorityPolicy.Job.HAUL,4,true)),1,new Random(1));
        assertEquals(CitizenPriorityPolicy.Job.HAUL,chosen.job());
    }
    @Test void fixedSeedReproducesStochasticSequence() {
        var cs=List.of(c(CitizenPriorityPolicy.Job.FARM,1,true),
                c(CitizenPriorityPolicy.Job.STUDY,2,true));
        Random left=new Random(12),right=new Random(12);
        for(int i=0;i<100;i++)
            assertEquals(CitizenPriorityPolicy.choose(cs,.8,left),
                    CitizenPriorityPolicy.choose(cs,.8,right));
    }
    @Test void noLegalActionReturnsNull() {
        assertNull(CitizenPriorityPolicy.choose(List.of(
                c(CitizenPriorityPolicy.Job.STUDY,0,true)),1,new Random(1)));
    }
}
