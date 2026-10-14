package dev.hearthbound.world;

import com.mojang.brigadier.CommandDispatcher;
import dev.hearthbound.ai.ActionGate;
import dev.hearthbound.ai.ColonyPolicy;
import dev.hearthbound.ai.PriorityPolicy;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.util.List;

/**
 * Minimal Minecraft embodiment: spawn a real villager and follow nearby players.
 * This intentionally does not claim to implement jobs, inventories or Create machinery.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class SableController {
    private static final String MARKER = "hearthbound.sable";
    private static final PriorityPolicy POLICY = new PriorityPolicy();

    private SableController() {}

    @SubscribeEvent
    public static void registerCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("sable")
            .requires(source -> source.hasPermission(2))
            .then(Commands.literal("spawn").executes(ctx -> {
                CommandSourceStack source = ctx.getSource();
                ServerLevel level = source.getLevel();
                Villager villager = EntityType.VILLAGER.create(level);
                if (villager == null) return 0;
                villager.moveTo(source.getPosition().x, source.getPosition().y,
                    source.getPosition().z, 0.0F, 0.0F);
                villager.getPersistentData().putBoolean(MARKER, true);
                villager.setCustomName(Component.literal("Sable"));
                villager.setCustomNameVisible(true);
                villager.setPersistenceRequired();
                if (!level.addFreshEntity(villager)) {
                    source.sendFailure(Component.literal("Unable to spawn Sable."));
                    return 0;
                }
                source.sendSuccess(() -> Component.literal("Sable spawned. She will follow nearby players."), true);
                return 1;
            })));
    }

    @SubscribeEvent
    public static void onLivingTick(LivingEvent.LivingTickEvent event) {
        if (!(event.getEntity() instanceof Villager villager)) return;
        if (!(villager.level() instanceof ServerLevel level)) return;
        if (!villager.getPersistentData().getBoolean(MARKER)) return;
        if (villager.tickCount % 20 != 0) return;

        Player target = level.getNearestPlayer(villager, 12.0D);
        if (target == null || target.isSpectator()) {
            villager.getNavigation().stop();
            return;
        }

        double distanceSquared = villager.distanceToSqr(target);
        boolean needsToFollow = distanceSquared > 9.0D && distanceSquared <= 144.0D;
        ColonyPolicy.Action follow = new ColonyPolicy.Action(
            "follow-nearest-player", ColonyPolicy.Kind.FOLLOW, 0, needsToFollow);
        ColonyPolicy.Observation snapshot = new ColonyPolicy.Observation(
            villager.tickCount, villager.getUUID().toString(), 0, 0, 0, List.of(follow));
        ColonyPolicy.Decision decision = POLICY.choose(snapshot);

        // This is the server-side authority boundary, not arbitrary policy-driven mutation.
        if (ActionGate.allowed(snapshot, decision) && "follow-nearest-player".equals(decision.actionId())) {
            villager.getNavigation().moveTo(target, 0.85D);
        } else if (distanceSquared <= 9.0D) {
            villager.getNavigation().stop();
        }
    }
}
