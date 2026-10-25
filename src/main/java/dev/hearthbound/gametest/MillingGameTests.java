package dev.hearthbound.gametest;

import com.simibubi.create.AllBlocks;
import com.simibubi.create.AllItems;
import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.integration.RuntimeInventoryDeltaChecks;
import dev.hearthbound.integration.ServerMillingActions;
import dev.hearthbound.integration.MillingObservationSavedData;
import dev.hearthbound.research.ScriptedMillingPolicy;
import dev.hearthbound.research.ScriptedMillingExecutor;
import dev.hearthbound.research.ScriptedCitizenWorkLoop;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import com.simibubi.create.content.kinetics.motor.CreativeMotorBlock;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;
import org.apache.logging.log4j.LogManager;

@GameTestHolder("hearthbound")
@PrefixGameTestTemplate(false)
public final class MillingGameTests {
    /**
     * Real navigation acceptance: no teleport or programmatic completion.
     * The Forge server tick controller must move a villager across solid terrain.
     */
    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 300)
    public static void realCitizenPathfinding(GameTestHelper helper) {
        var level = helper.getLevel();
        var server = level.getServer();
        // A wide, roofless, unobstructed platform so vanilla navigation has
        // room to turn and avoid adjacent GameTest structures.
        for (int x = 0; x <= 9; x++) {
            for (int z = 0; z <= 3; z++) {
                helper.setBlock(new BlockPos(x, 0, z), Blocks.STONE.defaultBlockState());
                for (int y = 1; y <= 4; y++)
                    helper.setBlock(new BlockPos(x, y, z), Blocks.AIR.defaultBlockState());
            }
        }
        BlockPos origin = helper.absolutePos(new BlockPos(1, 1, 1));
        BlockPos target = helper.absolutePos(new BlockPos(7, 1, 1));
        UUID citizenId = UUID.randomUUID();
        var registry = dev.hearthbound.integration.CitizenRegistrySavedData.get(server);
        registry.register(citizenId, "PathfindingFixture",
                level.dimension().location().toString(), origin.asLong(),
                dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        var villager = dev.hearthbound.integration.CitizenEmbodiment.spawn(level,citizenId,origin);
        villager.setNoAi(false);
        registry.assignMove(citizenId,level.dimension().location().toString(),target.asLong(),
                dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        helper.runAfterDelay(230, () -> {
            var actual = villager.blockPosition();
            var recorded = registry.snapshot().stream()
                    .filter(citizen -> citizen.id().equals(citizenId))
                    .findFirst().orElseThrow();
            var arrival = BlockPos.of(recorded.position());
            LogManager.getLogger().info(
                    "HEARTHBOUND_REAL_CITIZEN_NAVIGATION_CHECK citizen={} current={} observedArrival={} target={} arrivalDistanceSq={} task={} navigationDone={}",
                    citizenId, actual, arrival, target, arrival.distSqr(target),
                    recorded.task(), villager.getNavigation().isDone());
            // Vanilla villagers may resume wandering after the Hearthbound move
            // finishes. Assert the server-observed arrival at the time the
            // task transitioned to IDLE, not the entity's later idle position.
            helper.assertTrue("IDLE".equals(recorded.task())
                            && arrival.distSqr(target) <= 4
                            && arrival.distSqr(origin) > 4,
                    "Villager must physically reach worksite and record its arrival without teleportation"
                            + "; observed=" + arrival + " target=" + target);
            LogManager.getLogger().info(
                    "HEARTHBOUND_REAL_CITIZEN_NAVIGATION_PASS citizen={} from={} to={} arrived={}",
                    citizenId,origin,actual,true);
            pass(helper,"real_citizen_pathfinding");
        });
    }

    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 120)
    public static void scriptedCitizenMovement(GameTestHelper helper) {
        var level = helper.getLevel();
        var server = level.getServer();
        var registry = dev.hearthbound.integration.CitizenRegistrySavedData.get(server);
        UUID id = UUID.randomUUID();
        BlockPos origin = helper.absolutePos(new BlockPos(1, 1, 1));
        BlockPos target = helper.absolutePos(new BlockPos(4, 1, 1));
        registry.register(id,"MovementFixture",level.dimension().location().toString(),
                origin.asLong(),dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        var villager = dev.hearthbound.integration.CitizenEmbodiment.spawn(level,id,origin);
        registry.assignMove(id,level.dimension().location().toString(),target.asLong(),
                dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        helper.assertTrue(registry.snapshot().stream().anyMatch(c -> c.id().equals(id)
                        && c.task().equals("MOVE:" + target.asLong())),
                "Movement worksite must be registered");
        // Force a genuine world-position change and verify authoritative observation,
        // without relying on vanilla pathfinding through an unknown GameTest structure.
        villager.moveTo(target.getX()+0.5,target.getY(),target.getZ()+0.5,0,0);
        registry.observe(id,villager.blockPosition().asLong(),
                dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server),true);
        helper.assertTrue(registry.snapshot().stream().anyMatch(c -> c.id().equals(id)
                        && c.task().equals("IDLE") && c.position()==target.asLong()),
                "Actual entity position must be reflected in persistent citizen record");
        var reloaded=dev.hearthbound.integration.CitizenRegistrySavedData.load(
                registry.save(new CompoundTag()));
        helper.assertTrue(reloaded.snapshot().stream().anyMatch(c -> c.id().equals(id)
                        && c.position()==target.asLong() && c.task().equals("IDLE")),
                "Citizen arrival must survive NBT round trip");
        pass(helper,"scripted_citizen_movement");
    }

    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 100)
    public static void visibleCitizenEmbodiment(GameTestHelper helper) {
        var level = helper.getLevel();
        UUID id = UUID.randomUUID();
        BlockPos pos = helper.absolutePos(new BlockPos(1, 1, 1));
        var citizen = dev.hearthbound.integration.CitizenEmbodiment.spawn(level, id, pos);
        helper.assertTrue(citizen.isAlive() && id.equals(
                dev.hearthbound.integration.CitizenEmbodiment.identity(citizen)),
                "Spawned villager must retain citizen identity");
        helper.assertTrue(dev.hearthbound.integration.CitizenEmbodiment.find(level, id) != null,
                "Server must find visible citizen by persistent ID");
        pass(helper, "visible_citizen_embodiment");
    }

    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 40)
    public static void persistentCitizenRegistry(GameTestHelper helper) {
        var server = helper.getLevel().getServer();
        var registry = dev.hearthbound.integration.CitizenRegistrySavedData.get(server);
        var id = UUID.randomUUID();
        var record = registry.register(id, "FixtureSettler",
                helper.getLevel().dimension().location().toString(),
                helper.absolutePos(new BlockPos(1, 1, 1)).asLong(),
                dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        helper.assertTrue(registry.snapshot().stream().anyMatch(item -> item.id().equals(id)),
                "Citizen should appear in server-owned registry");
        var reloaded = dev.hearthbound.integration.CitizenRegistrySavedData.load(
                registry.save(new CompoundTag()));
        helper.assertTrue(reloaded.snapshot().stream().anyMatch(item -> item.equals(record)),
                "Citizen must survive NBT serialization");
        pass(helper, "persistent_citizen_registry");
    }

    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 40)
    public static void inventoryIdentity(GameTestHelper helper) {
        helper.assertTrue(RuntimeInventoryDeltaChecks.verify() == 8, "All eight inventory checks must execute");
        pass(helper, "inventory_identity");
    }

    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 220)
    public static void unpoweredMillstone(GameTestHelper helper) {
        MillstoneBlockEntity mill = place(helper);
        helper.runAfterDelay(200, () -> {
            helper.assertTrue(mill.getSpeed() == 0, "Unpowered fixture must remain stopped");
            helper.assertTrue(mill.inputInv.getStackInSlot(0).is(Items.WHEAT)
                    && mill.inputInv.getStackInSlot(0).getCount() == 1, "Unpowered wheat must remain");
            for (int i = 0; i < mill.outputInv.getSlots(); i++)
                helper.assertTrue(mill.outputInv.getStackInSlot(i).isEmpty(), "Unpowered output must be empty");
            pass(helper, "unpowered_millstone");
        });
    }

    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 500)
    public static void millingWithMotor(GameTestHelper helper) {
        MillstoneBlockEntity mill = place(helper);
        // Work-loop requests input transfer; the server adapter performs the mutation.
        mill.inputInv.setStackInSlot(0, ItemStack.EMPTY);
        ItemStack citizenHeld = new ItemStack(Items.WHEAT, 2);
        var supplyAction = ScriptedCitizenWorkLoop.tick(
                new ScriptedMillingExecutor.State(UUID.randomUUID(),
                        UUID.fromString("00000000-0000-0000-0000-000000000077"),
                        ScriptedMillingExecutor.Phase.UNASSIGNED),
                new ScriptedCitizenWorkLoop.Snapshot(true, true, false, true, true, false, false, false));
        helper.assertTrue(supplyAction.action() == ScriptedCitizenWorkLoop.Action.SUPPLY_WHEAT,
                "Scripted controller must request wheat transfer");
        helper.assertTrue(ServerMillingActions.supplyWheat(mill, citizenHeld)
                        && citizenHeld.getCount() == 1
                        && mill.inputInv.getStackInSlot(0).getCount() == 1,
                "Server inventory adapter must conserve wheat");
        helper.assertTrue(!ServerMillingActions.supplyWheat(mill, citizenHeld),
                "Occupied millstone cannot receive duplicate wheat");
        LogManager.getLogger().info("HEARTHBOUND_SCRIPTED_WORK_LOOP action=SUPPLY_WHEAT conserved=true");
        var durableIntent = MillingCheckpointFixture.prepare(mill);
        MillingDiscoveryFixture.claimMachine(helper.getLevel().getServer(), durableIntent);
        MillingDiscoveryFixture.acquireHandoff(helper.getLevel().getServer(), durableIntent);
        MillingDiscoveryFixture.beginObservationWindow(helper.getLevel().getServer(), durableIntent);
        MillingDiscoveryFixture.prepareAssignment(helper.getLevel().getServer(), durableIntent,
                mill.getLevel().dimension().location().toString(), mill.getBlockPos().asLong());
        // First scripted-policy-to-Create action boundary. The GameTest still supplies
        // the world fixture and assignment; no autonomous entity or pathfinding yet.
        var policyObservation = new ScriptedMillingPolicy.Observation(
                true, mill.inputInv.getStackInSlot(0).is(Items.WHEAT),
                true, true, false, false);
        var task = new ScriptedMillingExecutor.State(durableIntent.operationId(),
                UUID.fromString("00000000-0000-0000-0000-000000000077"),
                ScriptedMillingExecutor.Phase.UNASSIGNED);
        var workStep = ScriptedCitizenWorkLoop.tick(task,
                new ScriptedCitizenWorkLoop.Snapshot(true, false,
                        mill.inputInv.getStackInSlot(0).is(Items.WHEAT),
                        true, true, false, false, false));
        helper.assertTrue(workStep.action() == ScriptedCitizenWorkLoop.Action.ACTIVATE_POWER,
                "Tick-driven citizen must request motor power after wheat is in millstone");
        LogManager.getLogger().info(
                "HEARTHBOUND_SCRIPTED_WORK_LOOP action=ACTIVATE_POWER operation={}",
                durableIntent.operationId());
        var planned = ScriptedMillingExecutor.plan(task, policyObservation);
        helper.assertTrue(planned.authorizeMotorActivation()
                        && planned.state().phase() == ScriptedMillingExecutor.Phase.READY_TO_POWER,
                "Scripted citizen executor must authorize this milling operation");
        var activeTask = ScriptedMillingExecutor.powered(planned.state());
        helper.assertTrue(!ScriptedMillingExecutor.plan(activeTask, policyObservation).authorizeMotorActivation(),
                "A processing task cannot energize the motor twice");
        LogManager.getLogger().info(
                "HEARTHBOUND_SCRIPTED_MILLING_DECISION decision=PREPARE_MILLING operation={} phase=PROCESSING assigned=true",
                durableIntent.operationId());
        // Let the motor propagate its default 16 RPM through Create's kinetic network.
        BlockPos motorPos = new BlockPos(1, 0, 1);
        helper.setBlock(motorPos, AllBlocks.CREATIVE_MOTOR.getDefaultState()
                .setValue(CreativeMotorBlock.FACING, Direction.UP));
        helper.runAfterDelay(280, () -> {
            helper.assertTrue(Math.abs(mill.getSpeed()) == 16, "Motor must supply 16 RPM through its shaft");
            helper.assertTrue(mill.hasSource(), "Millstone must have a kinetic source");
            helper.assertTrue(mill.inputInv.getStackInSlot(0).isEmpty(), "Create must consume the wheat");
            int flour = 0;
            int seeds = 0;
            for (int i = 0; i < mill.outputInv.getSlots(); i++) {
                ItemStack stack = mill.outputInv.getStackInSlot(i);
                if (stack.is(AllItems.WHEAT_FLOUR.get())) flour += stack.getCount();
                else if (stack.is(Items.WHEAT_SEEDS)) seeds += stack.getCount();
                else helper.assertTrue(stack.isEmpty(), "Unexpected milling output");
            }
            helper.assertTrue(flour >= 1 && flour <= 3, "Wheat yields one guaranteed flour plus two independently rolled bonus items");
            helper.assertTrue(seeds <= 1, "Wheat yields at most one bonus seed");
            MillingObservationSavedData journal = MillingObservationSavedData.get(helper.getLevel().getServer());
            ListTag entries = journal.snapshot();
            CompoundTag observation = null;
            for (int i = 0; i < entries.size(); i++) {
                CompoundTag candidate = entries.getCompound(i);
                if (candidate.getLong("Position") == mill.getBlockPos().asLong()
                        && candidate.getString("Dimension").equals(mill.getLevel().dimension().location().toString())) {
                    helper.assertTrue(observation == null, "Exactly one observation for this machine");
                    observation = candidate;
                }
            }
            helper.assertTrue(observation != null, "Real milling must be recorded");
            helper.assertTrue(ItemStack.of(observation.getCompound("InputBefore")).is(Items.WHEAT),
                    "Journal must preserve consumed item identity");
            helper.assertTrue(observation.getString("Recipe").equals("create:milling/wheat"),
                    "Journal must retain Create's selected recipe");
            MillingObservationSavedData restored = MillingObservationSavedData.load(journal.save(new CompoundTag()));
            helper.assertTrue(restored.find(observation.getUUID("Id")).equals(observation),
                    "NBT round trip must retain complete observation");
            helper.assertTrue(!restored.append(observation), "Duplicate ID must be rejected after reload");
            long actualTick = observation.getLong("Tick");
            helper.assertTrue(restored.uniqueInWindow(observation.getString("Dimension"),
                            observation.getLong("Position"), actualTick, actualTick).equals(observation),
                    "Exact operation tick must resolve its own observation");
            CompoundTag second = observation.copy();
            second.putUUID("Id", UUID.randomUUID());
            second.putLong("Tick", actualTick + 1);
            helper.assertTrue(restored.append(second), "Second distinct operation observation must append");
            helper.assertTrue(restored.uniqueInWindow(observation.getString("Dimension"),
                            observation.getLong("Position"), actualTick + 1, actualTick + 1).equals(second),
                    "Later operation window must select only later observation");
            boolean ambiguousWindow = false;
            try {
                restored.uniqueInWindow(observation.getString("Dimension"),
                        observation.getLong("Position"), actualTick, actualTick + 1);
            } catch (IllegalStateException expected) { ambiguousWindow = true; }
            helper.assertTrue(ambiguousWindow, "Overlapping operation evidence must be rejected");

            CompoundTag conflict = observation.copy();
            conflict.putString("Recipe", "hearthbound:conflicting");
            boolean rejected = false;
            try { restored.append(conflict); } catch (IllegalArgumentException expected) { rejected = true; }
            helper.assertTrue(rejected, "Conflicting duplicate must fail");
            helper.setBlock(motorPos, Blocks.AIR.defaultBlockState());
            helper.runAfterDelay(20, () -> {
                helper.assertTrue(mill.getSpeed() == 0, "Removing the motor must stop rotation");
                mill.inputInv.setStackInSlot(0, new ItemStack(Items.WHEAT));
                helper.runAfterDelay(100, () -> {
                    helper.assertTrue(mill.getSpeed() == 0, "Disconnected millstone must stay stopped");
                    helper.assertTrue(mill.inputInv.getStackInSlot(0).is(Items.WHEAT)
                            && mill.inputInv.getStackInSlot(0).getCount() == 1,
                            "Disconnected millstone must not consume new wheat");
                    // Flush the real SavedData file before this JVM exits.
                    helper.getLevel().getServer().overworld().getDataStorage().save();
                    try {
                        net.minecraft.nbt.NbtIo.writeCompressed(journal.save(new CompoundTag()),
                                new java.io.File("milling-expected.nbt"));
                    } catch (java.io.IOException failure) {
                        throw new IllegalStateException("Cannot write restart expectation", failure);
                    }
                    MillingCheckpointFixture.checkpoint(mill, durableIntent);
                    pass(helper, "milling_motor_connection");
                });
            });
        });
    }

    /**
     * Two actual Create process() executions on the same physical millstone.
     * This checks live machine evidence only; separate durable citizen credits
     * are exercised by their own fixture and contract tests.
     */
    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 850)
    public static void consecutiveRealMillings(GameTestHelper helper) {
        MillstoneBlockEntity mill = place(helper);
        BlockPos motorPos = new BlockPos(1, 0, 1);
        var server = helper.getLevel().getServer();
        String dimension = mill.getLevel().dimension().location().toString();
        long position = mill.getBlockPos().asLong();
        UUID operationA = UUID.randomUUID();
        UUID operationB = UUID.randomUUID();
        long firstStart = dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server);
        helper.setBlock(motorPos, AllBlocks.CREATIVE_MOTOR.getDefaultState()
                .setValue(CreativeMotorBlock.FACING, Direction.UP));
        helper.runAfterDelay(280, () -> {
            helper.assertTrue(mill.inputInv.getStackInSlot(0).isEmpty(),
                    "First real milling must consume its input");
            long firstEnd = dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server);
            CompoundTag first = MillingObservationSavedData.get(server).uniqueInWindow(
                    dimension, position, firstStart, firstEnd);
            helper.assertTrue(first.getString("Recipe").equals("create:milling/wheat"),
                    "First operation must execute Create wheat milling");
            helper.assertTrue(first.getString("Quality").equals("positive_deltas"),
                    "First operation must have positive output evidence");
            helper.setBlock(motorPos, Blocks.AIR.defaultBlockState());
            helper.runAfterDelay(25, () -> {
                helper.assertTrue(mill.getSpeed() == 0, "Motor must stop between operations");
                helper.assertTrue(mill.inputInv.getStackInSlot(0).isEmpty(),
                        "Second input must not exist before supply");
                ItemStack held = new ItemStack(Items.WHEAT, 1);
                helper.assertTrue(ServerMillingActions.supplyWheat(mill, held) && held.isEmpty(),
                        "Second real wheat input must be conserved");
                long secondStart = dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server);
                helper.setBlock(motorPos, AllBlocks.CREATIVE_MOTOR.getDefaultState()
                        .setValue(CreativeMotorBlock.FACING, Direction.UP));
                helper.runAfterDelay(280, () -> {
                    helper.assertTrue(mill.inputInv.getStackInSlot(0).isEmpty(),
                            "Second real milling must consume its input");
                    long secondEnd = dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server);
                    CompoundTag second = MillingObservationSavedData.get(server).uniqueInWindow(
                            dimension, position, secondStart, secondEnd);
                    helper.assertTrue(!first.getUUID("Id").equals(second.getUUID("Id")),
                            "Real operations must have distinct observation IDs");
                    helper.assertTrue(second.getLong("Tick") > first.getLong("Tick"),
                            "Second real operation must occur after the first");
                    helper.assertTrue(second.getString("Recipe").equals("create:milling/wheat")
                                    && second.getString("Quality").equals("positive_deltas"),
                            "Second operation must produce real Create wheat flour");
                    boolean overlapRejected = false;
                    try {
                        MillingObservationSavedData.get(server).uniqueInWindow(
                                dimension, position, firstStart, secondEnd);
                    } catch (IllegalStateException expected) { overlapRejected = true; }
                    helper.assertTrue(overlapRejected,
                            "Cross-operation observation interval must fail closed");
                    try {
                        ConsecutiveMillingCredits.award(server, operationA,
                                ConsecutiveMillingCredits.FIRST, first);
                        ConsecutiveMillingCredits.award(server, operationB,
                                ConsecutiveMillingCredits.SECOND, second);
                        ConsecutiveMillingCredits.saveExpected(operationA, operationB, first, second);
                    } catch (java.io.IOException failure) {
                        throw new IllegalStateException("Two real citizen credits failed", failure);
                    }
                    helper.setBlock(motorPos, Blocks.AIR.defaultBlockState());
                    helper.getLevel().getServer().overworld().getDataStorage().save();
                    LogManager.getLogger().info(
                            "HEARTHBOUND_TWO_REAL_MILLINGS_PASS firstObservation={} secondObservation={} firstTick={} secondTick={} distinct=true",
                            first.getUUID("Id"), second.getUUID("Id"),
                            first.getLong("Tick"), second.getLong("Tick"));
                    pass(helper, "consecutive_real_millings");
                });
            });
        });
    }

    private static MillstoneBlockEntity place(GameTestHelper helper) {
        BlockPos pos = new BlockPos(1, 1, 1);
        helper.setBlock(pos, AllBlocks.MILLSTONE.getDefaultState());
        MillstoneBlockEntity mill = (MillstoneBlockEntity) helper.getBlockEntity(pos);
        mill.inputInv.setStackInSlot(0, new ItemStack(Items.WHEAT));
        return mill;
    }

    private static void pass(GameTestHelper helper, String name) {
        helper.succeed();
        LogManager.getLogger().info("HEARTHBOUND_GAMETEST_PASS {}", name);
    }
}
