# Citizen delivery no-replay restart acceptance

The prior experiment #40245141277 verified that the saved villager, operation receipt, wheat counter, work-order journal and actual Create input are recovered after a normal Minecraft restart.

This experiment now runs `CitizenSupplyInspection.inspect` against that **reloaded second-JVM world**. The first delivery has a matching receipt, but the test intentionally reassigns a second supply task to the occupied millstone before shutdown. Therefore the inspector must return `AMBIGUOUS_BLOCKED`, and no new supply may be authorized by reusing the previous attempt's receipt.

CI demands `HEARTHBOUND_CITIZEN_RESTART_NO_REPLAY_PASS` from the second server process. This is restart no-replay validation, **not** a power-loss or fault-injected crash test, and there is still no safe automatic operation retirement.
