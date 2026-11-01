# Research journal verification v0.7.13

A reproducible, Java 17-targeted script now compiles the *committed* pure Java research evidence and persistence code and executes the existing standalone suites in CI. Run locally with:

```bash
bash scripts/test-research-journals.sh
```

This script deliberately excludes Forge/MC classes from standalone compilation.

## Boundaries
- This does not compile the whole mod or prove Forge/Create API compatibility.
- It does not prove real Create receipt provenance, delayed taint handling, journal rollback detection, or cross-process exclusive locking.
- Existing legacy journals may be incompatible with the world binding and require an explicit migration.
- No automatic research rewards are enabled.

## Next acceptance gates
1. Green CI on the branch, plus a Forge Gradle compilation and GameTest.
2. Durable world/journal epoch reconciliation that detects mismatched snapshots.
3. Real server millstone operation leading to an attributed receipt.
4. Crash/restart recovery with no duplicate rewards.
