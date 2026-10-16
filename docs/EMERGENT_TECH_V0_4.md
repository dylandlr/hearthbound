# Emergent Technology Evidence Pipeline v0.4

## Goal

Technology discovery must emerge from physical experience rather than scripted global unlocks.

For the First Mill slice, the required causal chain is:

1. a citizen begins an experiment,
2. a real Create processing event consumes input and produces output,
3. that event becomes unique physical evidence,
4. contributing decisions receive personal / colony / research reward,
5. the experimenting citizen gains recipe knowledge,
6. the citizen can socially teach that knowledge to another citizen.

## Architecture

- `OutcomeLedger`: delayed causal credit with replay protection and separate reward domains.
- `WorldEvidenceJournal`: append-only verified machine outcomes.
- `CreateProcessingEvidenceAdapter`: Create-facing boundary; rejects observations unless input consumption and output production are both verified.
- `TechKnowledgeLedger`: per-citizen experiential recipe knowledge and teaching.
- `FirstMillResearchCoordinator`: joins experiment intent, physical evidence, reward, and knowledge.

The Create adapter intentionally does not depend on Create implementation classes. The eventual runtime hook should translate a confirmed server-side Create processing completion into a `VerifiedProcessingSnapshot`.

## Acceptance tests

The initial automated tests require that:

- verified wheat milling creates knowledge for Sable;
- Sable can teach the discovered milling recipe to Iven;
- replaying the same physical evidence cannot duplicate rewards;
- incomplete machine observations cannot become research evidence;
- decisions made after an event cannot receive causal credit.

## Next runtime slice

Implement the server-side Create hook that produces `VerifiedProcessingSnapshot` from a real millstone transaction, then persist `WorldEvidenceJournal` and citizen knowledge using Minecraft `SavedData`.

No test or headless simulation should be presented as proof of actual Minecraft gameplay. The gameplay acceptance remains a real client/server capture.
