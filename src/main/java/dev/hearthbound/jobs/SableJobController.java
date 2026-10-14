package dev.hearthbound.jobs;

import com.mojang.brigadier.Command;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import dev.hearthbound.HearthboundMod;

/**
 * Actual server-side movement probe, deliberately not a hauling/Create controller.
 * The assignment lives in the villager's persistent NBT across save/restart.
 */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID)
public final class SableJobController {
    private static final String TAG = "hearthbound.sable";
    private static final String TARGET = "HearthboundTarget";
    private static final String ACTIVE = "HearthboundTravelActive";

    private static final String RESULT = "HearthboundTravelResult";
    private static final Map<UUID, TravelProgress> PROGRESS = new HashMap<>();

    private SableJobController() {}

    public static void markSable(Villager villager) {
        villager.addTag(TAG);
    }

    public static int assign(CommandSourceStack source, BlockPos target) {
        ServerLevel level = source.getLevel();
        if (!level.hasChunkAt(target)) {
            source.sendFailure(Component.literal("Target chunk must be loaded."));
            return 0;
        }
        Villager sable = nearestSable(level, source.getPosition().x,
                source.getPosition().y, source.getPosition().z);
        if (sable == null) {
            source.sendFailure(Component.literal("No Hearthbound Sable within 32 blocks."));
            return 0;
        }
        var data = sable.getPersistentData();
        data.putLong(TARGET, target.asLong());
        data.putBoolean(ACTIVE, true);
        data.putString(RESULT, "MOVING");
        PROGRESS.remove(sable.getUUID());
        sable.getNavigation().stop();
        source.sendSuccess(() -> Component.literal("Sable assigned a travel destination at " +
                target.toShortString() + ". This is pathfinding only; no item transfers."), false);
        return Command.SINGLE_SUCCESS;
    }

    public static int cancel(CommandSourceStack source) {
        Villager sable = nearestSable(source.getLevel(), source.getPosition().x,
                source.getPosition().y, source.getPosition().z);
        if (sable == null) {
            source.sendFailure(Component.literal("No Hearthbound Sable within 32 blocks."));
            return 0;
        }
        sable.getPersistentData().putBoolean(ACTIVE, false);
        sable.getPersistentData().putString(RESULT, "CANCELLED");
        PROGRESS.remove(sable.getUUID());
        sable.getNavigation().stop();
        source.sendSuccess(() -> Component.literal("Cancelled Sable's travel job."), false);
        return 1;
    }

    private static Villager nearestSable(ServerLevel level, double x, double y, double z) {
        AABB bounds = new AABB(x - 32, y - 16, z - 32, x + 32, y + 16, z + 32);
        Villager best = null;
        double bestDistance = Double.MAX_VALUE;
        for (Villager villager : level.getEntitiesOfClass(Villager.class, bounds,
                entity -> entity.getTags().contains(TAG))) {
            double d = villager.distanceToSqr(x, y, z);
            if (d < bestDistance) {
                bestDistance = d;
                best = villager;
            }
        }
        return best;
    }

    @SubscribeEvent
    public static void onLivingTick(LivingEvent.LivingTickEvent event) {
        Entity entity = event.getEntity();
        if (!(entity instanceof Villager sable) || sable.level().isClientSide()
                || !sable.getTags().contains(TAG)) return;

        var data = sable.getPersistentData();
        if (!data.getBoolean(ACTIVE)) return;
        // A bounded low-frequency navigator, never force-loads destination chunks.
        if (sable.tickCount % 20 != 0) return;
        BlockPos target = BlockPos.of(data.getLong(TARGET));
        if (!sable.level().hasChunkAt(target)) {
            sable.getNavigation().stop();
            return;
        }
        double distanceSq = sable.distanceToSqr(target.getX() + 0.5, target.getY(), target.getZ() + 0.5);
        long gameTick = sable.level().getGameTime();
        TravelProgress watch = PROGRESS.computeIfAbsent(sable.getUUID(),
                id -> new TravelProgress(gameTick, distanceSq));
        TravelProgress.Outcome outcome = watch.sample(gameTick, distanceSq);
        if (outcome != TravelProgress.Outcome.MOVING) {
            data.putBoolean(ACTIVE, false);
            data.putString(RESULT, outcome.name());
            PROGRESS.remove(sable.getUUID());
            sable.getNavigation().stop();
            return;
        }
        sable.getNavigation().moveTo(target.getX() + 0.5, target.getY(),
                target.getZ() + 0.5, 1.0);
    }
}
