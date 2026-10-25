# Scripted citizen work loop v1

A pure-Java bounded tick step translates an assigned milling task and limited world observation into one of NONE, SUPPLY_WHEAT, ACTIVATE_POWER, OBSERVE, REPORT_COMPLETION, or ABORT. It carries operation and citizen identity through the existing executor states and refuses unauthorized/unsafe/credited tasks. Six standalone checks exercise progression and failure guards.

The existing Forge GameTest now requires the work loop to request ACTIVATE_POWER before the fixture installs Create's creative motor. The log verifier requires that action once. Earlier real Create milling and citizen-credit restart tests are preserved.

This is **not yet a fully embodied Minecraft citizen**: no pathfinding, NPC entity, inventory transfer, continuous per-tick Forge controller, or autonomous neural policy exists. GameTest still supplies the wheat and creates the motor after authorization. Next implementation should add real server tick scheduling and a world-action adapter, with explicit power and inventory mutation authorities, and preserve the same operation identity and evidence.
