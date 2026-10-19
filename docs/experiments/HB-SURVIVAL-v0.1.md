# Hearthbound survival baseline v0.1

Implementation status: local Java policy and existing kernel/ledger/lifecycle checks passed. Forge compilation, physical acceptance and updated capture are pending publication/CI. Do not report a new Minecraft run until those checks finish.

## What this slice changes

Citizens opt into persistent hunger (0–20), one-second survival decisions, visible-food acquisition, food consumption, visible-monster responses, and local night-cover discovery. The baseline policy is deliberately scripted. Its inputs and outputs are isolated in `ai/SurvivalPolicy.java` for later replacement/comparison with a trained actor.

Food is consumed from the citizen's actual inventory or a reachable visible dropped item. Supported foods: bread, apple, carrot, baked potato. Seeking food uses normal navigation. One actual item is removed per meal; carried work cargo is never eaten. Hunger decreases 0.02 per live second, with starvation damage at zero. This is custom villager physiology; vanilla villagers do not have player hunger mechanics. Offline time does not generate starvation.

Visible threats within 12 blocks trigger fight or flight. Danger/combat instincts choose the response; below 60% health citizens retreat regardless of combat confidence. Defense applies real Minecraft damage (2 per second within 2 blocks). Flee attempts eight reachable destinations. No successful path is claimed when navigation fails.

At night, shelter-sensitive citizens scan loaded blocks within 8 horizontal / 2 vertical blocks for standable roof cover. A roof is **not proof of a monster-proof shelter**. The current slice neither builds shelter nor guarantees survival. A cached target is revalidated and no chunks are force-loaded.

## Authority and interruption

Survival decisions execute before the work controller. While survival owns navigation, both hauling and library execution are suspended. Existing cargo, job UUIDs, inventory claims and reservations remain intact. Work resumes through its existing executor after the survival action releases control. Existing restart quarantine remains unchanged. Library travel can time out after a prolonged emergency; study progress is not awarded during suspension.

Repeated hauling is separately opt-in. The next job may be offered only after the previous exact UUID/destination has completed with no remaining cargo. Default one-shot behavior remains compatible with the original eight-citizen baseline.

## Operator commands

Run as/near the intended citizen (operator permission required):

- `/sable survival-on`, `/sable survival-off`, `/sable survival-inspect`
- `/sable auto-work-repeat-on`, `/sable auto-work-repeat-off`
- Existing work configuration and `/sable auto-work-on` still authorize hauling endpoints.

State is in `ForgeData."hearthbound.survivalV1"`. It includes food, enabled flag, current action/outcome, meals, confirmed hits and the last 32 decision/outcome events. Instincts remain in their existing persistent profile. These are debug/experimental controls, not the planned player GUI.

## Physical acceptance contract

`scripts/survival-server-test.py` runs after the existing server smoke suite:

1. Eat a real dropped apple: confirm one meal and removal of the item entity.
2. Cautious profile chooses flight from a visible zombie.
3. Confident healthy profile causes actual combat damage.
4. Injuring that citizen changes its response to flight.
5. Navigate under a nearby roof at night; release work at dawn.
6. Deliver three real wheat through distinct completed jobs and personal event memories.
7. Interrupt an in-flight cargo job for cover; assert original UUID and item retained; resume and verify one physical delivery.

The graphical workflow retains the original eight-citizen work checks, then records this controlled one-citizen survival test. This is not an eight-citizen survival benchmark. Physical checks are pass/fail integration tests, not performance or emergence measurements.

## Next learning experiment

Freeze these mechanics before BC/PPO training. Use disjoint world/population seeds and compare random legal, scripted, BC and BC+PPO intention selection with identical executors. Separate personal and colony outcome rewards. Measure survival, nutrition acquired, damage taken/dealt, work completion, interruptions and invalid actions. Distilling this rule policy from synthetic observations alone must be labeled imitation of a scripted teacher, not learned Minecraft strategy.

Still absent: trained policy, autonomous farming/crafting, meaningful age progression, reproduction, faction-valued reputation, social communication, management GUI and social-web renderer. No society-emergence claim is justified by this slice.
