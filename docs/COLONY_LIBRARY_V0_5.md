# Hearthbound Colony Library — architecture v0.5

## Player experience
Citizens can visit bookshelves, read compatible mod manuals, take study notes,
and later teach other citizens. A public library becomes a social and technical
institution. Access depends on ownership, literacy, distance, study time, and
colony policy; specialist teachers accelerate practical learning.

## Crucial distinction
Book reading creates theoretical knowledge, NOT proof a citizen can operate a
machine. Physical experiments retain authority for practical confidence and
Create processing rewards. Reading confidence is capped at 0.40.

## Implemented in this slice
- `CitizenTechnologyKnowledge.study(...)`: persistent per-citizen book-source
  knowledge (READ_BOOK) with book provenance and lower confidence.
- `LibraryStudyCatalog`: explicit, versioned, mod-book-to-lesson mappings,
  server-validated session contract, literacy and study-time requirements,
  access rejection, and duplicate-session protection.
- JUnit tests for reading and denial cases.

## Not implemented yet
- Actual Patchouli / Create Ponder / other guidebook content adapters.
- Server-side verification of bookshelf contents, book possession or completed
  study time; callers must provide verified facts, not trust client messages.
- Library blocks, librarians, travel/animation, borrowing, content persistence,
  lesson scheduling, and gameplay E2E validation.

## Content adapters
Avoid claiming that a GUI instruction page is a recipe. Connect supported
public datapack/registry materials and curated versioned book metadata via
mod-specific adapters. Never silently infer unavailable content. Ponder scenes
are in-world tutorials, not necessarily in-game books. Respect compatibility
and avoid extracting restricted prose or assets.

## Next acceptance
Place a registered manual in a library shelf; Sable navigates there, spends
time reading, gains capped theory; then performs the real physical experiment
to advance mastery. Iven must not learn when the book is absent, inaccessible,
or the study session was interrupted.
