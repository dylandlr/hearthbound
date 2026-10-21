package dev.hearthbound.research;

import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

class ResearchDecisionTraceJournalTest {
    private static ResearchDecisionTraceJournal.Trace trace(String id, long tick) {
        return new ResearchDecisionTraceJournal.Trace(1, id, tick,
            new ResearchDecisionTraceJournal.PolicyDecision("PROPOSE", "wheat", 0.5),
            new ResearchDecisionTraceJournal.PolicyDecision("DEFER", null, 0.2),
            true, "threshold");
    }
    @Test void boundedSnapshotsRemainDetached() {
        var journal = new ResearchDecisionTraceJournal(2);
        journal.append(trace("sable", 1));
        var before = journal.snapshot("sable");
        journal.append(trace("sable", 2));
        journal.append(trace("sable", 3));
        assertEquals(1, before.size());
        assertEquals(List.of(2L, 3L), journal.snapshot("sable").stream()
            .map(ResearchDecisionTraceJournal.Trace::gameTick).toList());
        assertThrows(UnsupportedOperationException.class, () -> before.clear());
    }
    @Test void duplicateAndReorderedTicksFailEvenAfterEviction() {
        var journal = new ResearchDecisionTraceJournal(1);
        journal.append(trace("sable", 4));
        journal.append(trace("sable", 5));
        assertThrows(IllegalArgumentException.class, () -> journal.append(trace("sable", 4)));
        assertThrows(IllegalArgumentException.class, () -> journal.append(trace("sable", 5)));
        journal.append(trace("other", 4));
        assertEquals(1, journal.snapshot("other").size());
    }
    @Test void sameObservationProducesInspectableTrace() {
        var candidate = new ExperimentSelectionPolicy.Candidate("wheat","wheat","millstone",
            "flour",0.4,0.2,true,true,false);
        var observation = new ExperimentSelectionPolicy.Observation(1,0.05,1,0.1,List.of(candidate));
        var journal = new ResearchDecisionTraceJournal(3);
        journal.record("sable", 21, ResearchDecisionComparison.evaluate(observation));
        var item = journal.snapshot("sable").get(0);
        assertTrue(item.disagreement());
        assertEquals("PROPOSE", item.scripted().action());
        assertEquals("DEFER", item.personality().action());
        assertTrue(journal.exportJson().contains("\"gameTick\":21"));
    }
    @Test void jsonEscapesCitizenIds() {
        var journal = new ResearchDecisionTraceJournal(1);
        journal.append(trace("a\"\\\n", 0));
        assertTrue(journal.exportJson().contains("a\\\"\\\\\\n"));
        assertThrows(IllegalArgumentException.class, () -> new ResearchDecisionTraceJournal(0));
        assertThrows(IllegalArgumentException.class, () ->
            new ResearchDecisionTraceJournal.PolicyDecision("PROPOSE", "wheat", Double.NaN));
    }
}
