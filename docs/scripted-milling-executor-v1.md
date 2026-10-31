# Scripted milling executor v1

The first scripted task coordinator is a pure, deterministic state machine. It takes an operation UUID, citizen UUID, policy observation and current phase. Only a valid PREPARE_MILLING decision from an active, assigned task can authorize initial motor activation. Missing resources wait; unsafe/unassigned/credited work aborts. Processing and completed tasks cannot reactivate the motor.

The existing Minecraft GameTest now consults this executor before placing the Create motor and asserts that a processing task cannot authorize a second activation. Standalone contracts additionally check replay, missing resources, unauthorized tasks and mismatched completion operation IDs.

**Not yet accomplished:** the fixture citizen has no embodied Minecraft entity, physical navigation, inventory interaction, or continuous tick-driven controller. The test still places the motor block once the scripted policy authorizes it. Executor state is not persisted across restart yet. The citizen credit GameTest is separate from task completion and cannot prove self-directed learning.

The next acceptance gate is a Minecraft GameTest run showing the executor authorization marker, actual wheat flour delta, citizen credit and restart markers together. Only then wire a server-managed citizen action controller with phase transitions, retries and bounded observations.
