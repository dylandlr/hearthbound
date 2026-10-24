package dev.hearthbound.gametest;

import com.simibubi.create.AllBlocks;
import com.simibubi.create.AllItems;
import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.integration.RuntimeInventoryDeltaChecks;
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
            helper.setBlock(motorPos, Blocks.AIR.defaultBlockState());
            helper.runAfterDelay(20, () -> {
                helper.assertTrue(mill.getSpeed() == 0, "Removing the motor must stop rotation");
                mill.inputInv.setStackInSlot(0, new ItemStack(Items.WHEAT));
                helper.runAfterDelay(100, () -> {
                    helper.assertTrue(mill.getSpeed() == 0, "Disconnected millstone must stay stopped");
                    helper.assertTrue(mill.inputInv.getStackInSlot(0).is(Items.WHEAT)
                            && mill.inputInv.getStackInSlot(0).getCount() == 1,
                            "Disconnected millstone must not consume new wheat");
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
