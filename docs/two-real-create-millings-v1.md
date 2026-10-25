# Two genuine Create milling operations — acceptance v1

A new `consecutiveRealMillings` Forge GameTest powers a millstone, verifies that Minecraft Create consumed its first wheat and emitted an authoritative processing observation, removes motor power, transfers a second real wheat into the same block entity using the server adapter, reactivates the motor, and requires a second real consumption and positive flour output. The observations must have distinct UUIDs, strictly ordered server ticks, and nonoverlapping observation windows. A deliberately broad window containing both must reject ambiguity.

The dedicated-server smoke verifier now requires **three actual millstone mutation log events** (one from the prior attributed-credit fixture, two from the new consecutive-milling fixture) and the `HEARTHBOUND_TWO_REAL_MILLINGS_PASS` marker. The evidence manifest records this marker.

**This does not yet award independent research credits to both cycles of the new GameTest.** The two operations are real Create process mutations, but remain driven by fixture control. The original separate test still awards one fixed citizen a durable credit. Next is to give each real operation a separate durable intent, machine generation, citizen assignment and receipt, and verify both credits after Minecraft restart.
