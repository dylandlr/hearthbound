# Citizen entity restart diagnostic

Minecraft acceptance #40242510107 failed in the second JVM with `Citizen entity missing after restart`, while earlier work-order and attempt checks passed. The new trial explicitly marks spawned citizen villagers persistent and defers the entity verifier until 80 server ticks have elapsed. This distinguishes immediate startup timing from missing saved entity data.

If the villager is still absent, investigate GameTest structure/entity cleanup before asserting persistence. A dedicated non-GameTest fixture entity may be needed for saved-world restart testing. The verifier must not synthesize or respawn a missing citizen to pass this test.
