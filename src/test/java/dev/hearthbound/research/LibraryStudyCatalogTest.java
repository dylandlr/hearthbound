package dev.hearthbound.research;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

final class LibraryStudyCatalogTest {
    private LibraryStudyCatalog catalog() {
        LibraryStudyCatalog catalog = new LibraryStudyCatalog();
        catalog.registerBook(new LibraryStudyCatalog.Book(
                "patchouli:guide_book", "example-v1",
                java.util.List.of(new LibraryStudyCatalog.Lesson(
                        "hearthbound:power_transmission",
                        "create:shaft",
                        200,
                        20))));
        return catalog;
    }

    private LibraryStudyCatalog.Session session(boolean hasBook, boolean access, long end, int literacy) {
        return new LibraryStudyCatalog.Session(
                "session-1", "sable", "patchouli:guide_book",
                "hearthbound:power_transmission", 10, end, literacy, hasBook, access);
    }

    @Test void readingCreatesLowConfidenceTheoryNotPracticalProof() {
        var result = catalog().complete(session(true, true, 210, 60));
        assertEquals("create:shaft", result.recipeId());
        assertEquals("reading:session-1", result.evidenceId());
        assertTrue(result.theoreticalConfidence() <= 0.4);
    }

    @Test void noBookNoAccessNoLearning() {
        assertThrows(IllegalStateException.class, () -> catalog().complete(session(false, true, 210, 60)));
        assertThrows(IllegalStateException.class, () -> catalog().complete(session(true, false, 210, 60)));
    }

    @Test void requireEnoughStudyAndLiteracy() {
        assertThrows(IllegalStateException.class, () -> catalog().complete(session(true, true, 20, 60)));
        assertThrows(IllegalStateException.class, () -> catalog().complete(session(true, true, 210, 5)));
    }

    @Test void repeatSessionCannotMintMoreEvidence() {
        var catalog = catalog();
        var first = catalog.complete(session(true, true, 210, 60));
        assertEquals(first, catalog.complete(session(true, true, 210, 60)));
        assertEquals(1, catalog.completedCount());
        assertThrows(IllegalStateException.class, () -> catalog.complete(session(true, true, 210, 80)));
    }
}
