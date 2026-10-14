# Integration policy

This branch contains the cumulative changes from PRs #6 through #15, based on PR #15's head. The single review PR to `main` is intended as an alternative to reviewing/merging the entire dependent stack individually. Do NOT merge both approaches without reconciling duplicate commits.

## Gates before treating the milestone as playable
- Forge compilation CI: green on this exact branch.
- Pure Java policy and ledger regression: green on this exact branch.
- Manual `runClient` test: Sable spawn, navigation, one wheat haul, output-blocked recovery, graceful world restart.
- Two-player dedicated server smoke test: not yet run.
- Crash conservation: not yet safe, so testing only with disposable wheat.

Known correctness issues should be filed and reproduced with logs and exact commit SHA. A successful compile does not count as a successful Minecraft playtest.
