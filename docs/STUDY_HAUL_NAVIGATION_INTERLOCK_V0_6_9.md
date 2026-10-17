# Hearthbound v0.6.9 — Study/haul navigation interlock

This patch closes three physical executor entry-point conflicts:

1. SableHauling.assign refuses a citizen whose autonomous study is TRAVELING or whose library runtime is STUDYING. No source claims or mill reservations are acquired in this case.
2. LibraryStudyRuntime.begin refuses citizens with an active haul, even when an operator directly starts studying rather than using the policy bridge.
3. SableController's follow-player navigation yields while a library task is traveling or studying. This prevents follow movement competing with the study executor.

The existing LibraryPolicyBridge.consider refuses an active haul, while
AutonomousLibraryStudy.assign also guards hauling. The new checks cover the
reverse direction and bypass of the bridge.

## Minecraft acceptance checks
- Assign a library journey to Sable, then try /sable haul: reject without claiming source.
- Put Sable near a book, start manual study, then try /sable haul: reject.
- Start a haul, then try /hearthbound library study: reject.
- While Sable travels to study, stand nearby and move: following must not hijack navigation.
- When study is finished or interrupted, following may resume.
- Ensure a quarantined/paused haul still blocks study until manually reconciled.
- Confirm successful delivery does not duplicate or lose cargo.
- Reboot mid-study and verify lease restoration and subsequent completion.

## Remaining work
These are coordinated executor interlocks, not yet a single world-scoped
persisted task manager; separate existing controllers are retained.
A Forge compile, runtime checks and a real two-choice priority arbitration
experiment remain required. Do not claim the test plan has passed.
