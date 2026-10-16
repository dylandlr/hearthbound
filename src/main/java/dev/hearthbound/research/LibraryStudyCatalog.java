package dev.hearthbound.research;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * A curated, versioned index of public mod-book topics. Entries describe what a book
 * teaches; they do not generate recipes, grant items, or scrape client-only UI.
 * The caller must verify the physical book's presence and a completed study session.
 */
public final class LibraryStudyCatalog {
    public record Lesson(String topicId, String recipeId, int requiredStudyTicks, int minimumLiteracy) {
        public Lesson {
            if (topicId == null || topicId.isBlank() || recipeId == null || recipeId.isBlank())
                throw new IllegalArgumentException("Lesson IDs are required");
            if (requiredStudyTicks < 1 || minimumLiteracy < 0 || minimumLiteracy > 100)
                throw new IllegalArgumentException("Invalid lesson requirements");
        }
    }
    public record Book(String bookItemId, String contentVersion, List<Lesson> lessons) {
        public Book {
            if (bookItemId == null || bookItemId.isBlank()
                    || contentVersion == null || contentVersion.isBlank())
                throw new IllegalArgumentException("Book identity/version required");
            lessons = List.copyOf(Objects.requireNonNull(lessons));
        }
    }
    public record Session(
            String sessionId, String citizenId, String bookItemId,
            String topicId, long startTick, long endTick, int literacy,
            boolean bookVerified, boolean libraryAccessible) {}
    public record ReadingEvidence(
            String evidenceId, String citizenId, String bookItemId,
            String topicId, String recipeId, String contentVersion,
            double theoreticalConfidence) {}

    private final Map<String, Book> books = new LinkedHashMap<>();
    private final Map<String, ReadingEvidence> completed = new LinkedHashMap<>();

    public synchronized void registerBook(Book book) {
        Objects.requireNonNull(book);
        Book existing = books.putIfAbsent(book.bookItemId(), book);
        if (existing != null && !existing.equals(book))
            throw new IllegalStateException("Book ID is already registered");
    }

    /** Book permission, pathfinding, inventory and reading time are supplied by a server adapter. */
    public synchronized ReadingEvidence complete(Session session) {
        Objects.requireNonNull(session);
        if (session.sessionId() == null || session.sessionId().isBlank()
                || session.citizenId() == null || session.citizenId().isBlank())
            throw new IllegalArgumentException("Session identity required");
        Book book = books.get(session.bookItemId());
        if (book == null) throw new IllegalArgumentException("Book is not cataloged");
        if (!session.bookVerified() || !session.libraryAccessible())
            throw new IllegalStateException("Physical library/book access not verified");
        if (session.startTick() < 0 || session.endTick() < session.startTick())
            throw new IllegalArgumentException("Invalid study interval");
        Lesson lesson = book.lessons().stream()
                .filter(x -> x.topicId().equals(session.topicId()))
                .findFirst().orElseThrow(() -> new IllegalArgumentException("Topic absent from book"));
        if (session.literacy() < lesson.minimumLiteracy())
            throw new IllegalStateException("Literacy requirement not met");
        if (session.endTick() - session.startTick() < lesson.requiredStudyTicks())
            throw new IllegalStateException("Study session was too short");
        String key = session.sessionId();
        ReadingEvidence evidence = new ReadingEvidence(
                "reading:" + key, session.citizenId(), book.bookItemId(),
                lesson.topicId(), lesson.recipeId(), book.contentVersion(),
                0.10 + 0.30 * (session.literacy() / 100.0));
        ReadingEvidence prior = completed.putIfAbsent(key, evidence);
        if (prior != null && !prior.equals(evidence))
            throw new IllegalStateException("Conflicting duplicate study session");
        return prior == null ? evidence : prior;
    }

    public synchronized int completedCount() { return completed.size(); }
}
