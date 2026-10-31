# Processing Evidence Gate v0.4

This is an LLM-free, Java 17-compatible validation boundary supporting First Mill research evidence. It is **not** wired to Create events or persistent storage yet.

## Compile standalone smoke checks
```sh
mkdir -p out
javac --release 17 -d out src/main/java/dev/hearthbound/evidence/ProcessingEvidenceGate.java src/test/java/dev/hearthbound/evidence/ProcessingEvidenceGateTest.java
java -cp out dev.hearthbound.evidence.ProcessingEvidenceGateTest
```

## Trusted boundary
Only submit machine operation receipts collected on the authoritative Minecraft server after actual processing commits. Input/output deltas are necessary but not sufficient evidence: the Create adapter must correlate these deltas to the same processing transaction and machine, and distinguish automation routing from consumption/production.

The CreditSink must atomically enforce durable uniqueness for evidence ID and reward credit in one transaction. The in-memory gate is not a substitute for this. Restore persisted evidence IDs before ingestion after restart.

## Next acceptance gates
- Real powered Create millstone + real wheat -> flour, verified from world events.
- Blocked output does not create successful evidence.
- Duplicate and post-restart replay have zero additional effect.
- Discoverer can teach a second citizen; learning measured via independent follow-up execution.
- Run server/client end-to-end playtest and report seed, versions, ticks and evidence IDs.
