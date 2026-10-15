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
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Disposable single-run world test. Uses real tick-driven citizen hauling code. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID)
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
    private static boolean restartScenario;
    private static BlockPos pickupFeet;
    private static BlockPos deliveryFeet;
    private HaulE2EProbe() {}

    public static int start(CommandSourceStack command) {
        restartScenario = false;
        return startScenario(command, false, false);
    }

    public static int startOnSource(CommandSourceStack command) {
        restartScenario = false;
        return startScenario(command, false, false, true);
    }

    public static int startFullDestination(CommandSourceStack command) {
        restartScenario = false;
        return startScenario(command, true, false);
    }

    public static int startBlockAfterPickup(CommandSourceStack command) {
        restartScenario = false;
        return startScenario(command, false, true);
    }

    public static int startRestart(CommandSourceStack command) {
        restartScenario = true;
        return startScenario(command, false, true);
    }

    private static int startScenario(CommandSourceStack command, boolean fillOutput, boolean blockAfterPickup) {
        return startScenario(command, fillOutput, blockAfterPickup, false);
    }

    private static int startScenario(CommandSourceStack command, boolean fillOutput,
            boolean blockAfterPickup, boolean spawnOnSource) {
        ServerLevel level = command.getLevel();
        BlockPos spawn = level.getSharedSpawnPos();
        int y = level.getHeight(net.minecraft.world.level.levelgen.Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                spawn.getX(), spawn.getZ()) + 3;
        BlockPos base = new BlockPos(spawn.getX(), y, spawn.getZ());
        // An empty dedicated server stops entity ticks after 300 ticks unless
        // it has a player or forced chunks. Spawn chunks alone are insufficient.
        // Keep only this disposable acceptance arena ticking, including after
        // save/restart. Production hauling never creates these chunk tickets.
        for (int chunkX = (base.getX() - 2) >> 4; chunkX <= (base.getX() + 12) >> 4; chunkX++)
            for (int chunkZ = (base.getZ() - 2) >> 4; chunkZ <= (base.getZ() + 2) >> 4; chunkZ++)
                level.setChunkForced(chunkX, chunkZ, true);
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
        citizen.moveTo(spawnOnSource ? sourcePos.getX() + .5 : base.getX() + .5,
                spawnOnSource ? sourcePos.getY() + 1 : base.getY(), base.getZ() + .5, 0, 0);
        citizen.setCustomName(Component.literal("Sable [E2E]"));
        citizen.setPersistenceRequired();
        if (restartScenario) citizen.addTag("hearthbound.restart.probe");
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
        pickupFeet = null;
        deliveryFeet = null;
        command.sendSuccess(() -> Component.literal("HB_HAUL_E2E_STARTED tickingChunks="
                + level.getForcedChunks().size()), false);
        return 1;
    }

    /** Observe exact transfer ticks, before movement can obscure where it happened. */
    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void observe(LivingEvent.LivingTickEvent event) {
        if (event.getEntity() != citizen || testLevel == null) return;
        var state = citizen.getPersistentData();
        int cargo = state.getCompound("HearthboundHaul").getInt("Cargo");
        if (cargo > 0) {
            observedPickup = true;
            if (pickupFeet == null) pickupFeet = citizen.blockPosition().immutable();
            if (citizen.distanceToSqr(destinationPos.getX() + .5,
                    destinationPos.getY() + .5, destinationPos.getZ() + .5) > 6.25)
                observedDeliveryTravel = true;
        } else if (observedPickup && !state.contains("HearthboundHaul", 10) && deliveryFeet == null) {
            deliveryFeet = citizen.blockPosition().immutable();
        }
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
                    + " cargo=" + cargo + " dest=" + to
                    + " phase=" + state.getCompound("HearthboundHaul").getString("Phase")
                    + " result=" + state.getCompound("HearthboundHaul").getString("Result")
                    + " paused=" + state.getCompound("HearthboundHaul").getBoolean("Paused")
                    + " alive=" + citizen.isAlive()
                    + " entityTick=" + citizen.tickCount
                    + " worldTick=" + testLevel.getGameTime()
                    + " pos=" + citizen.position()
                    + " destination=" + destinationPos.toShortString()), false);
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
            if (pickupFeet == null || deliveryFeet == null
                    || !besideStation(pickupFeet, sourcePos) || !besideStation(deliveryFeet, destinationPos))
                return fail(command, "interaction_on_station pickup=" + pickupFeet + " delivery=" + deliveryFeet);
            command.sendSuccess(() -> Component.literal("HB_HAUL_E2E_PASS source=4 dest=4 cargo=0 approachedBeside=true"
                    + " pickup=" + pickupFeet.toShortString() + " delivery=" + deliveryFeet.toShortString()), false);
            return 1;
        }
        command.sendSuccess(() -> Component.literal("HB_HAUL_E2E_PENDING source=" + from
                + " dest=" + to + " cargo=" + cargo
                + " pickupSeen=" + observedPickup + " travelingSeen=" + observedDeliveryTravel), false);
        return 1;
    }

    private static boolean besideStation(BlockPos feet, BlockPos station) {
        return Math.abs(feet.getX() - station.getX()) + Math.abs(feet.getZ() - station.getZ()) == 1
                && Math.abs(feet.getY() - station.getY()) <= 1;
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
