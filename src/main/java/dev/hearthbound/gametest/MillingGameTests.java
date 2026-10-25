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
