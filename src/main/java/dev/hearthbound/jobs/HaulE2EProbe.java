package dev.hearthbound.jobs;

import dev.hearthbound.HearthboundMod;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;

/** Disposable single-run world test. Uses real tick-driven citizen hauling code. */
public final class HaulE2EProbe {
    private static BlockPos sourcePos;
    private static BlockPos destinationPos;
    private static Villager citizen;
    private static ServerLevel testLevel;
    private static boolean observedPickup;
    private static boolean observedDeliveryTravel;
    private static boolean fullDestinationMode;
    private static boolean blockAfterPickupMode;
    private static boolean destinationFilledAfterPickup;
    private HaulE2EProbe() {}

    public static int start(CommandSourceStack command) {
        return startScenario(command, false, false);
    }

    public static int startFullDestination(CommandSourceStack command) {
        return startScenario(command, true, false);
    }

    public static int startBlockAfterPickup(CommandSourceStack command) {
        return startScenario(command, false, true);
    }

    private static int startScenario(CommandSourceStack command, boolean fillOutput, boolean blockAfterPickup) {
        ServerLevel level = command.getLevel();
        BlockPos spawn = level.getSharedSpawnPos();
        int y = level.getHeight(net.minecraft.world.level.levelgen.Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                spawn.getX(), spawn.getZ()) + 3;
        BlockPos base = new BlockPos(spawn.getX(), y, spawn.getZ());
        // Safe isolated elevated test platform. Only used in disposable CI world.
        for (int x = -2; x <= 12; x++)
            for (int z = -2; z <= 2; z++) {
                level.setBlockAndUpdate(base.offset(x, -1, z), Blocks.STONE.defaultBlockState());
                for (int dy = 0; dy <= 2; dy++)
                    level.setBlockAndUpdate(base.offset(x, dy, z), Blocks.AIR.defaultBlockState());
            }
        sourcePos = base.offset(2, 0, 0);
        destinationPos = base.offset(9, 0, 0);
        level.setBlockAndUpdate(sourcePos, Blocks.BARREL.defaultBlockState());
        level.setBlockAndUpdate(destinationPos, Blocks.BARREL.defaultBlockState());
        if (!(level.getBlockEntity(sourcePos) instanceof BarrelBlockEntity input)
                || !(level.getBlockEntity(destinationPos) instanceof BarrelBlockEntity)) return fail(command, "barrels");
        input.setItem(0, new ItemStack(Items.WHEAT, 8));
        if (fillOutput) {
            BarrelBlockEntity output = (BarrelBlockEntity) level.getBlockEntity(destinationPos);
            for (int slot = 0; slot < output.getContainerSize(); slot++)
                output.setItem(slot, new ItemStack(Items.COBBLESTONE, 64));
        }
        citizen = EntityType.VILLAGER.create(level);
        if (citizen == null) return fail(command, "villager");
        citizen.moveTo(base.getX() + 0.5, base.getY(), base.getZ() + 0.5, 0, 0);
        citizen.setCustomName(Component.literal("Sable [E2E]"));
        citizen.setPersistenceRequired();
        if (blockAfterPickup) citizen.addTag("hearthbound.restart.probe");
        SableJobController.markSable(citizen);
        if (!level.addFreshEntity(citizen) ||
                !BarrelHaulController.assignCitizen(citizen, sourcePos, destinationPos, 4))
            return fail(command, "job");
        testLevel = level;
        fullDestinationMode = fillOutput;
        blockAfterPickupMode = blockAfterPickup;
        destinationFilledAfterPickup = false;
        observedPickup = false;
        observedDeliveryTravel = false;
        command.sendSuccess(() -> Component.literal("HB_HAUL_E2E_STARTED"), false);
        return 1;
    }

    public static int check(CommandSourceStack command) {
        if (citizen == null || testLevel != command.getLevel() ||
                !(testLevel.getBlockEntity(sourcePos) instanceof BarrelBlockEntity input) ||
                !(testLevel.getBlockEntity(destinationPos) instanceof BarrelBlockEntity output))
            return fail(command, "not_started");
        int from = countWheat(input);
        int to = countWheat(output);
        var state = citizen.getPersistentData();
        int cargo = state.contains("HearthboundHaul", 10)
                ? state.getCompound("HearthboundHaul").getInt("Cargo") : 0;
        if (from + to + cargo != 8) return fail(command, "inventory_conservation");
        if (blockAfterPickupMode) {
            if (!destinationFilledAfterPickup && from == 4 && cargo == 4 && to == 0) {
                for (int slot = 0; slot < output.getContainerSize(); slot++)
                    output.setItem(slot, new ItemStack(Items.COBBLESTONE, 64));
                destinationFilledAfterPickup = true;
            }
            boolean carrying = state.contains("HearthboundHaul", 10)
                    && state.getCompound("HearthboundHaul").getInt("Cargo") == 4;
            boolean outputBlocked = carrying
                    && "OUTPUT_FULL_CARRYING".equals(state.getCompound("HearthboundHaul").getString("Result"));
            if (destinationFilledAfterPickup && outputBlocked && from == 4 && to == 0 && cargo == 4) {
                command.sendSuccess(() -> Component.literal("HB_HAUL_CARGO_BLOCKED_PASS source=4 cargo=4 dest=0"), false);
                return 1;
            }
            command.sendSuccess(() -> Component.literal("HB_HAUL_CARGO_BLOCKED_PENDING source=" + from
                    + " cargo=" + cargo + " dest=" + to), false);
            return 1;
        }
        if (fullDestinationMode) {
            boolean fullOfCobblestone = true;
            for (int slot = 0; slot < output.getContainerSize(); slot++) {
                ItemStack stack = output.getItem(slot);
                if (!stack.is(Items.COBBLESTONE) || stack.getCount() != 64) {
                    fullOfCobblestone = false;
                    break;
                }
            }
            boolean noWheatLost = from == 8 && to == 0 && cargo == 0 && fullOfCobblestone;
            boolean rejected = state.contains("HearthboundHaul", 10)
                    && "PICKUP".equals(state.getCompound("HearthboundHaul").getString("Phase"))
                    && "OUTPUT_FULL".equals(state.getCompound("HearthboundHaul").getString("Result"));
            if (noWheatLost && rejected) {
                command.sendSuccess(() -> Component.literal("HB_HAUL_FULL_PASS source=8 dest=0 cargo=0"), false);
                return 1;
            }
            command.sendSuccess(() -> Component.literal("HB_HAUL_FULL_PENDING source=" + from
                    + " dest=" + to + " cargo=" + cargo), false);
            return 1;
        }
        if (from == 4 && cargo == 4 && to == 0) observedPickup = true;
        if (observedPickup && cargo > 0 && citizen.distanceToSqr(destinationPos.getX() + .5,
                destinationPos.getY() + .5, destinationPos.getZ() + .5) > 6.25)
            observedDeliveryTravel = true;
        if (from == 4 && to == 4 && cargo == 0 && !state.contains("HearthboundHaul", 10)
                && observedPickup && observedDeliveryTravel) {
            command.sendSuccess(() -> Component.literal("HB_HAUL_E2E_PASS source=4 dest=4 cargo=0"), false);
            return 1;
        }
        command.sendSuccess(() -> Component.literal("HB_HAUL_E2E_PENDING source=" + from
                + " dest=" + to + " cargo=" + cargo
                + " pickupSeen=" + observedPickup + " travelingSeen=" + observedDeliveryTravel), false);
        return 1;
    }

    private static int countWheat(BarrelBlockEntity barrel) {
        int total = 0;
        for (int slot = 0; slot < barrel.getContainerSize(); slot++) {
            ItemStack stack = barrel.getItem(slot);
            if (stack.is(Items.WHEAT)) total += stack.getCount();
        }
        return total;
    }

    private static int fail(CommandSourceStack command, String cause) {
        command.sendFailure(Component.literal("HB_HAUL_E2E_FAIL " + cause));
        return 0;
    }
}
