package dev.hearthbound.research;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class TechnologyHypothesesTest {
    private WorldEvidenceJournal journal() {
        var journal = new WorldEvidenceJournal();
        journal.append(new WorldEvidenceJournal.ProcessingEvidence(
            "physical-1", 20, "overworld", "create:millstone", "0,64,0",
            "minecraft:wheat", 1, "create:wheat_flour", 1,
            "create:milling/wheat", true));
        return journal;
    }
    @Test void verifiedEvidenceConfirmsMatchingConjecture() {
        var ledger=new TechnologyHypotheses();
        ledger.propose("Sable","create:milling/wheat","minecraft:wheat",
            "create:millstone","create:wheat_flour");
        assertEquals(TechnologyHypotheses.Status.PROPOSED,
            ledger.require("Sable","create:milling/wheat").status());
        assertEquals(TechnologyHypotheses.Status.CONFIRMED,
            ledger.observe("Sable","create:milling/wheat","physical-1",journal()).status());
    }
    @Test void mismatchFalsifiesWithoutUnlocking() {
        var ledger=new TechnologyHypotheses();
        ledger.propose("Sable","create:milling/wheat","minecraft:wheat",
            "create:millstone","minecraft:bread");
        assertEquals(TechnologyHypotheses.Status.FALSIFIED,
            ledger.observe("Sable","create:milling/wheat","physical-1",journal()).status());
    }
    @Test void unrelatedEvidenceCannotConfirm() {
        var ledger=new TechnologyHypotheses();
        ledger.propose("Sable","create:mixing/dough","minecraft:wheat",
            "create:millstone","create:wheat_flour");
        assertThrows(IllegalArgumentException.class,()->
            ledger.observe("Sable","create:mixing/dough","physical-1",journal()));
    }
    @Test void unknownEvidenceAndConflictingHypothesesRejected() {
        var ledger=new TechnologyHypotheses();
        ledger.propose("Sable","create:milling/wheat","minecraft:wheat",
            "create:millstone","create:wheat_flour");
        assertThrows(IllegalArgumentException.class,()->
            ledger.observe("Sable","create:milling/wheat","nonexistent",journal()));
        assertThrows(IllegalStateException.class,()->
            ledger.propose("Sable","create:milling/wheat","minecraft:carrot",
                "create:millstone","create:wheat_flour"));
    }
    @Test void evidenceReplayIsIdempotent() {
        var ledger=new TechnologyHypotheses(); var journal=journal();
        ledger.propose("Sable","create:milling/wheat","minecraft:wheat",
            "create:millstone","create:wheat_flour");
        var first=ledger.observe("Sable","create:milling/wheat","physical-1",journal);
        assertEquals(first,ledger.observe("Sable","create:milling/wheat","physical-1",journal));
    }
}
