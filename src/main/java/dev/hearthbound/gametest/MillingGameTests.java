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
    /**
     * Integration across a physically navigated citizen and Create's server
     * inventory primitive. Test controls the supply action after arrival.
     */
    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 330)
    public static void citizenWalksAndSuppliesMill(GameTestHelper helper) {
        var level = helper.getLevel();
        var server = level.getServer();
        for (int x = 0; x <= 9; x++) for (int z = 0; z <= 3; z++) {
            helper.setBlock(new BlockPos(x, 0, z), Blocks.STONE.defaultBlockState());
            for (int y = 1; y <= 4; y++)
                helper.setBlock(new BlockPos(x, y, z), Blocks.AIR.defaultBlockState());
        }
        BlockPos origin = helper.absolutePos(new BlockPos(1, 1, 1));
        BlockPos destination = helper.absolutePos(new BlockPos(7, 1, 1));
        // Place real Create machinery adjacent to the designated worksite.
        helper.setBlock(new BlockPos(8, 1, 1), AllBlocks.MILLSTONE.getDefaultState());
        var mill = (MillstoneBlockEntity) level.getBlockEntity(helper.absolutePos(new BlockPos(8, 1, 1)));
        helper.assertTrue(mill != null, "Create millstone must exist as a real block entity");
        UUID citizenId = UUID.randomUUID();
        var registry = dev.hearthbound.integration.CitizenRegistrySavedData.get(server);
        registry.register(citizenId, "MillWorkerFixture",level.dimension().location().toString(),
                origin.asLong(),dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        var villager = dev.hearthbound.integration.CitizenEmbodiment.spawn(level,citizenId,origin);
        villager.setNoAi(false);
        villager.getPersistentData().putInt("HearthboundWheat", 2);
        helper.assertTrue(!dev.hearthbound.integration.CitizenSupplyAssignment.isAuthorized(
                        server,citizenId,level.dimension().location().toString(),destination.offset(1,0,0)),
                "Unprepared citizen operation cannot authorize supply");
        try {
            dev.hearthbound.integration.CitizenSupplyAssignment.prepare(
                    server,citizenId,level.dimension().location().toString(),destination.offset(1,0,0));
        } catch(java.io.IOException error) {
            throw new IllegalStateException(error);
        }
        helper.assertTrue(dev.hearthbound.integration.CitizenSupplyAssignment.isAuthorized(
                        server,citizenId,level.dimension().location().toString(),destination.offset(1,0,0)),
                "Prepared citizen work order must be recoverable before moving or supplying");
        registry.assignMillSupply(citizenId,level.dimension().location().toString(),destination.asLong(),
                dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        helper.runAfterDelay(5, () -> {
            helper.assertTrue(mill.inputInv.getStackInSlot(0).isEmpty(),
                    "Citizen must not supply millstone before physically arriving");
            helper.assertTrue(villager.getPersistentData().getInt("HearthboundWheat")==2,
                    "Citizen wheat cannot be debited before arrival");
        });
        helper.runAfterDelay(230, () -> {
            var citizen = registry.snapshot().stream().filter(item -> item.id().equals(citizenId))
                    .findFirst().orElseThrow();
            BlockPos observedArrival = BlockPos.of(citizen.position());
            helper.assertTrue(citizen.task().equals("IDLE")
                            && observedArrival.distSqr(destination) <= 4
                            && observedArrival.distSqr(origin) > 4,
                    "Physical citizen must have navigated and reached worksite before supply");
            helper.assertTrue(mill.inputInv.getStackInSlot(0).is(Items.WHEAT)
                            && mill.inputInv.getStackInSlot(0).getCount()==1,
                    "Tick-driven citizen must have supplied real Create millstone");
            helper.assertTrue(villager.getPersistentData().getInt("HearthboundWheat")==1,
                    "Exactly one wheat must be debited from citizen entity inventory");
            try {
                var persistedOperation=dev.hearthbound.integration.CitizenSupplyAssignment.require(
                        server,citizenId,level.dimension().location().toString(),mill.getBlockPos());
                helper.assertTrue(dev.hearthbound.integration.CitizenSupplyAttempt.hasAttempt(
                        server,persistedOperation),"A durable attempt must precede real Create mutation");
            } catch(java.io.IOException failure) {
                throw new IllegalStateException("Missing durable delivery evidence",failure);
            }
            helper.assertTrue(citizen.task().equals("IDLE"),
                    "Successful server-tick supply must finish task without repeated transfer");
            helper.assertTrue(dev.hearthbound.integration.CitizenSupplyInspection.inspect(
                    server,citizenId,level.dimension().location().toString(),
                    mill.getBlockPos(),villager,mill)
                    == dev.hearthbound.integration.CitizenSupplyRecovery.Decision.COMPLETED_OBSERVED,
                    "Live recovery inspection must recognize the same durable operation receipt");
            helper.assertTrue(villager.getPersistentData().getLong("HearthboundLastSupplyMill")
                            == mill.getBlockPos().asLong()
                            && villager.getPersistentData().getLong("HearthboundLastSupplyTick") > 0,
                    "Real server supply must retain the machine and logical tick on citizen entity");
            var roundTrip = dev.hearthbound.integration.CitizenRegistrySavedData.load(
                    registry.save(new CompoundTag()));
            helper.assertTrue(roundTrip.snapshot().stream().anyMatch(item -> item.id().equals(citizenId)
                            && item.task().equals("IDLE")
                            && item.position()==citizen.position()),
                    "Completed supply task must round-trip through Minecraft SavedData");

            LogManager.getLogger().info(
                    "HEARTHBOUND_CITIZEN_REAL_WALK_SUPPLY_PASS citizen={} arrival={} mill={} movedWheat=1 conserved=true controller=server_tick",
                    citizenId,observedArrival,mill.getBlockPos());
            // Submit a second funded request while the machine is still
            // occupied. It must neither consume citizen wheat nor complete.
            registry.assignMillSupply(citizenId,level.dimension().location().toString(),
                    destination.asLong(),
                    dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
            helper.runAfterDelay(30, () -> {
                helper.assertTrue(villager.getPersistentData().getInt("HearthboundWheat")==1
                                && mill.inputInv.getStackInSlot(0).getCount()==1,
                        "Occupied millstone must not consume a second citizen wheat");
                helper.assertTrue(registry.snapshot().stream().anyMatch(item -> item.id().equals(citizenId)
                                && item.task().startsWith("MILL_SUPPLY:")),
                        "Blocked milling task must remain outstanding for recovery");
                try {
                    CitizenSupplyRestartFixture.write(server,citizenId,
                            level.dimension().location().toString(),mill.getBlockPos(),villager.blockPosition(),1);
                } catch(java.io.IOException failure) {
                    throw new IllegalStateException("Could not stage citizen restart evidence",failure);
                }
                pass(helper,"citizen_walks_and_supplies_mill");
            });
        });
    }

    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 40)
    public static void citizenSupplyRecoveryContract(GameTestHelper helper) {
        var recovery=dev.hearthbound.integration.CitizenSupplyRecovery.classify(
                new dev.hearthbound.integration.CitizenSupplyRecovery.Evidence(
                        true,true,1,2,true,true));
        helper.assertTrue(recovery==dev.hearthbound.integration.CitizenSupplyRecovery.Decision.COMPLETED_OBSERVED,
                "Durable attempt and matching completed-operation receipt must classify as completed");
        var uncertain=dev.hearthbound.integration.CitizenSupplyRecovery.classify(
                new dev.hearthbound.integration.CitizenSupplyRecovery.Evidence(
                        true,false,2,2,false,false));
        helper.assertTrue(uncertain==dev.hearthbound.integration.CitizenSupplyRecovery.Decision.AMBIGUOUS_BLOCKED,
                "Interrupted attempt must never auto-replay");
        var missingReceipt=dev.hearthbound.integration.CitizenSupplyRecovery.classify(
                new dev.hearthbound.integration.CitizenSupplyRecovery.Evidence(
                        true,true,1,2,false,true));
        helper.assertTrue(missingReceipt==dev.hearthbound.integration.CitizenSupplyRecovery.Decision.AMBIGUOUS_BLOCKED,
                "Wheat count and machine input alone cannot prove operation identity");
        pass(helper,"citizen_supply_recovery_contract");
    }

    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 40)
    public static void citizenSupplyInterruptionBoundaries(GameTestHelper helper) {
        var recovery=dev.hearthbound.integration.CitizenSupplyRecovery.class;
        for(var point:dev.hearthbound.integration.CitizenSupplyRecovery.InterruptionPoint.values()) {
            var decision=dev.hearthbound.integration.CitizenSupplyRecovery.interrupted(point);
            var expected=point==dev.hearthbound.integration.CitizenSupplyRecovery.InterruptionPoint.BEFORE_ATTEMPT
                    ? dev.hearthbound.integration.CitizenSupplyRecovery.Decision.NOT_STARTED
                    : dev.hearthbound.integration.CitizenSupplyRecovery.Decision.AMBIGUOUS_BLOCKED;
            helper.assertTrue(decision==expected,
                    "Interruption must never authorize blind mutation replay at " + point);
        }
        pass(helper,"citizen_supply_interruption_boundaries");
    }

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
                    citizenId,origin,arrival,true);
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

    /**
     * Real Create output-handler integration, without minting output inside
     * the production extraction primitive. A fixture supplies processed
     * output as the controlled starting state.
     */
    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 40)
    public static void millstoneOutputExtractionConservesItems(GameTestHelper helper) {
        helper.setBlock(new BlockPos(1,1,1), AllBlocks.MILLSTONE.getDefaultState());
        var mill=(MillstoneBlockEntity)helper.getBlockEntity(new BlockPos(1,1,1));
        helper.assertTrue(mill!=null,"Create millstone output fixture must exist");
        mill.outputInv.setStackInSlot(0,new ItemStack(Items.WHEAT,3));
        var first=ServerMillingActions.collectOutput(mill,0,2);
        helper.assertTrue(first.is(Items.WHEAT) && first.getCount()==2,
                "Citizen must collect exactly two items from real Create output");
        helper.assertTrue(mill.outputInv.getStackInSlot(0).getCount()==1,
                "Exactly one item must remain in the output handler");
        var second=ServerMillingActions.collectOutput(mill,0,10);
        helper.assertTrue(second.is(Items.WHEAT) && second.getCount()==1,
                "Second extraction must be capped to actual remaining items");
        helper.assertTrue(mill.outputInv.getStackInSlot(0).isEmpty(),
                "Output handler must be empty after removing all three items");
        helper.assertTrue(ServerMillingActions.collectOutput(mill,0,1).isEmpty()
                        && ServerMillingActions.collectOutput(mill,-1,1).isEmpty(),
                "Empty or invalid output extraction cannot create items");
        pass(helper,"millstone_output_extraction_conserves_items");
    }

    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 100)
    public static void citizenCollectsRealMillstoneOutput(GameTestHelper helper) {
        var level=helper.getLevel();
        var server=level.getServer();
        helper.setBlock(new BlockPos(1,0,1),Blocks.STONE.defaultBlockState());
        helper.setBlock(new BlockPos(2,0,1),Blocks.STONE.defaultBlockState());
        helper.setBlock(new BlockPos(2,1,1),AllBlocks.MILLSTONE.getDefaultState());
        var mill=(MillstoneBlockEntity)helper.getBlockEntity(new BlockPos(2,1,1));
        helper.assertTrue(mill!=null,"Real Create millstone must exist");
        mill.outputInv.setStackInSlot(0,new ItemStack(Items.WHEAT,2));
        BlockPos worker=helper.absolutePos(new BlockPos(1,1,1));
        UUID id=UUID.randomUUID();
        var registry=dev.hearthbound.integration.CitizenRegistrySavedData.get(server);
        registry.register(id,"CollectorFixture",level.dimension().location().toString(),
                worker.asLong(),dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        var villager=dev.hearthbound.integration.CitizenEmbodiment.spawn(level,id,worker);
        registry.assignMillCollect(id,level.dimension().location().toString(),worker.asLong(),
                dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        helper.runAfterDelay(60,()-> {
            var citizen=registry.snapshot().stream().filter(item->item.id().equals(id))
                    .findFirst().orElseThrow();
            helper.assertTrue("IDLE".equals(citizen.task()),
                    "Server-tick citizen controller must complete real millstone collection");
            helper.assertTrue(mill.outputInv.getStackInSlot(0).isEmpty(),
                    "Real Create output must be depleted, not duplicated");
            var data=villager.getPersistentData();
            helper.assertTrue(data.hasUUID("HearthboundLastCollectionOperation"),
                    "Citizen must retain operation receipt");
            var collected=ItemStack.of(data.getCompound("HearthboundMillCollected"));
            helper.assertTrue(collected.is(Items.WHEAT) && collected.getCount()==2,
                    "Actual collected items must be owned by the real villager");
            pass(helper,"citizen_collects_real_millstone_output");
        });
    }

    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 100)
    public static void citizenDeliversCollectedOutputToChest(GameTestHelper helper) {
        var level=helper.getLevel();
        var server=level.getServer();
        helper.setBlock(new BlockPos(1,0,1),Blocks.STONE.defaultBlockState());
        helper.setBlock(new BlockPos(2,0,1),Blocks.STONE.defaultBlockState());
        helper.setBlock(new BlockPos(2,1,1),Blocks.CHEST.defaultBlockState());
        BlockPos worker=helper.absolutePos(new BlockPos(1,1,1));
        var chest=(net.minecraft.world.level.block.entity.ChestBlockEntity)
                helper.getBlockEntity(new BlockPos(2,1,1));
        helper.assertTrue(chest!=null,"Real chest fixture required");
        UUID id=UUID.randomUUID();
        var registry=dev.hearthbound.integration.CitizenRegistrySavedData.get(server);
        registry.register(id,"StockpileFixture",level.dimension().location().toString(),
                worker.asLong(),dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        var villager=dev.hearthbound.integration.CitizenEmbodiment.spawn(level,id,worker);
        var carried=new ItemStack(Items.WHEAT,2);
        var tag=new CompoundTag();
        carried.save(tag);
        villager.getPersistentData().put("HearthboundMillCollected",tag);
        villager.getPersistentData().putUUID("HearthboundLastCollectionOperation",UUID.randomUUID());
        registry.assignStockpileDelivery(id,level.dimension().location().toString(),
                worker.asLong(),dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        helper.runAfterDelay(60,()->{
            var citizen=registry.snapshot().stream().filter(item->item.id().equals(id))
                    .findFirst().orElseThrow();
            helper.assertTrue("IDLE".equals(citizen.task()),"Citizen must finish stockpile work");
            helper.assertTrue(chest.getItem(0).is(Items.WHEAT) && chest.getItem(0).getCount()==2,
                    "Real stockpile must receive exactly the collected two items");
            helper.assertTrue(!villager.getPersistentData().contains("HearthboundMillCollected"),
                    "Citizen must not retain duplicate carried goods");
            helper.assertTrue(villager.getPersistentData().hasUUID("HearthboundLastStockpileOperation"),
                    "Citizen must retain durable stockpile handoff operation");
            pass(helper,"citizen_delivers_collected_output_to_chest");
        });
    }

    @GameTest(templateNamespace = "hearthbound", template = "empty", timeoutTicks = 120)
    public static void citizenChainsCollectionIntoStockpile(GameTestHelper helper) {
        var level=helper.getLevel();
        var server=level.getServer();
        helper.setBlock(new BlockPos(1,0,1),Blocks.STONE.defaultBlockState());
        helper.setBlock(new BlockPos(2,0,1),Blocks.STONE.defaultBlockState());
        helper.setBlock(new BlockPos(2,1,1),AllBlocks.MILLSTONE.getDefaultState());
        helper.setBlock(new BlockPos(2,1,3),Blocks.CHEST.defaultBlockState());
        var mill=(MillstoneBlockEntity)helper.getBlockEntity(new BlockPos(2,1,1));
        var chest=(net.minecraft.world.level.block.entity.ChestBlockEntity)
                helper.getBlockEntity(new BlockPos(2,1,3));
        helper.assertTrue(mill!=null && chest!=null,"Real millstone and chest required");
        mill.outputInv.setStackInSlot(0,new ItemStack(Items.WHEAT,2));
        BlockPos worker=helper.absolutePos(new BlockPos(1,1,1));
        BlockPos stockpileApproach=helper.absolutePos(new BlockPos(1,1,3));
        UUID id=UUID.randomUUID();
        var registry=dev.hearthbound.integration.CitizenRegistrySavedData.get(server);
        registry.register(id,"ChainedProductionFixture",level.dimension().location().toString(),
                worker.asLong(),dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        var villager=dev.hearthbound.integration.CitizenEmbodiment.spawn(level,id,worker);
        villager.getPersistentData().putLong("HearthboundStockpileTarget",stockpileApproach.asLong());
        registry.assignMillCollect(id,level.dimension().location().toString(),worker.asLong(),
                dev.hearthbound.integration.ForgeServerTickObserver.logicalTick(server));
        helper.runAfterDelay(90,()->{
            var citizen=registry.snapshot().stream().filter(item->item.id().equals(id))
                    .findFirst().orElseThrow();
            helper.assertTrue("IDLE".equals(citizen.task()),
                    "Citizen must finish both collection and storage without manual reassignment");
            helper.assertTrue(mill.outputInv.getStackInSlot(0).isEmpty(),
                    "Collected goods must leave the actual Create millstone");
            helper.assertTrue(chest.getItem(0).is(Items.WHEAT) && chest.getItem(0).getCount()==2,
                    "Real chest must contain exactly two collected items");
            helper.assertTrue(!villager.getPersistentData().contains("HearthboundMillCollected"),
                    "No duplicate cargo may remain after chained delivery");
            helper.assertTrue(villager.getPersistentData().hasUUID("HearthboundLastStockpileOperation"),
                    "Storage handoff must be journaled");
            pass(helper,"citizen_chains_collection_into_stockpile");
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
