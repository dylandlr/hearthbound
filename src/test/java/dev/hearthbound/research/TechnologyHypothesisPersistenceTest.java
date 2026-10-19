package dev.hearthbound.research;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;
class TechnologyHypothesisPersistenceTest {
    @Test void exactSnapshotRoundTrip() {
        TechnologyHypotheses first=new TechnologyHypotheses();
        first.propose("citizen-a","create:milling/wheat","minecraft:wheat",
                      "create:millstone","create:wheat_flour");
        TechnologyHypotheses restored=new TechnologyHypotheses();
        restored.restore(first.snapshot());
        assertEquals(first.snapshot(),restored.snapshot());
    }
    @Test void corruptSnapshotIsRejectedWithoutPartialMutation() {
        TechnologyHypotheses store=new TechnologyHypotheses();
        store.propose("a","r","i","m","o");
        var before=store.snapshot();
        assertThrows(IllegalArgumentException.class,()->store.restore(List.of(
           new TechnologyHypotheses.Hypothesis("b","r","i","m","o",
                TechnologyHypotheses.Status.CONFIRMED,null))));
        assertEquals(before,store.snapshot());
    }
    @Test void duplicatedRecordsRejected() {
        TechnologyHypotheses store=new TechnologyHypotheses();
        var entry=new TechnologyHypotheses.Hypothesis("b","r","i","m","o",
            TechnologyHypotheses.Status.PROPOSED,null);
        assertThrows(IllegalArgumentException.class,()->store.restore(List.of(entry,entry)));
    }
}
