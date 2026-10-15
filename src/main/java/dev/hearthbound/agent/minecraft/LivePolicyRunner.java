package dev.hearthbound.agent.minecraft;

import dev.hearthbound.HearthboundMod;
import dev.hearthbound.agent.v02.InferenceCadenceV02;
import dev.hearthbound.agent.v02.MillObservation;
import dev.hearthbound.agent.v02.MillObservationEncoder;
import dev.hearthbound.agent.v02.PolicyDecisionV02;
import dev.hearthbound.agent.v02.ScriptedMillPolicyV02;
import dev.hearthbound.jobs.SableSelection;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/** Opt-in, bounded scripted inference runner. Learned policies will use the same boundary. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID)
public final class LivePolicyRunner {
    public static final String VERSION = "hearthbound.agent.live-runner.v0.2";
    private static final String ENABLED = "HearthboundAgentPolicyEnabled";
    private static final String LAST_TICK = "HearthboundAgentLastDecisionTick";
    private static final String ORDER = "HearthboundMillOrder";
    private static final int TRACE_LIMIT = 256;
    private static final Logger LOGGER = LogManager.getLogger();
    private static final ScriptedMillPolicyV02 POLICY = new ScriptedMillPolicyV02();
    private static final Map<UUID, ArrayDeque<String>> TRACES = new LinkedHashMap<>();

    private LivePolicyRunner() {}

    public static boolean enabled(Villager worker) {
        return worker.getPersistentData().getBoolean(ENABLED);
    }

    public static int enable(CommandSourceStack source) {
        Villager worker = nearestOrder(source);
        if (worker == null) return fail(source, "No First Mill worker within 32 blocks.");
        CompoundTag data = worker.getPersistentData();
        data.putBoolean(ENABLED, true);
        data.putLong(LAST_TICK, -1);
        source.sendSuccess(() -> Component.literal(
                "Agent v0.2 scripted policy enabled for " + worker.getName().getString()
                + "; legacy high-level scheduling paused."), false);
        return 1;
    }

    public static int disable(CommandSourceStack source) {
        Villager worker = nearestOrder(source);
        if (worker == null) return fail(source, "No First Mill worker within 32 blocks.");
        worker.getPersistentData().putBoolean(ENABLED, false);
        source.sendSuccess(() -> Component.literal(
                "Agent policy disabled; legacy First Mill scheduling restored."), false);
        return 1;
    }

    public static int status(CommandSourceStack source) {
        Villager worker = nearestOrder(source);
        if (worker == null) return fail(source, "No First Mill worker within 32 blocks.");
        int count = TRACES.getOrDefault(worker.getUUID(), new ArrayDeque<>()).size();
        source.sendSuccess(() -> Component.literal("Agent runner=" + (enabled(worker) ? "enabled" : "disabled")
                + ", policy=scripted-v0.2, traces=" + count
                + ", lastDecisionTick=" + worker.getPersistentData().getLong(LAST_TICK)), false);
        return 1;
    }

    public static int dump(CommandSourceStack source) {
        Villager worker = nearestOrder(source);
        if (worker == null) return fail(source, "No First Mill worker within 32 blocks.");
        ArrayDeque<String> traces = TRACES.get(worker.getUUID());
        if (traces == null || traces.isEmpty()) return fail(source, "No live agent traces recorded.");
        String last = traces.peekLast();
        LOGGER.info("HB_AGENT_TRACE_DUMP worker={} count={}", worker.getUUID(), traces.size());
        for (String trace : traces) LOGGER.info("HB_AGENT_TRACE {}", trace);
        source.sendSuccess(() -> Component.literal("Wrote " + traces.size()
                + " bounded agent traces to the server log. Last: " + last), false);
        return 1;
    }

    @SubscribeEvent
    public static void tick(LivingEvent.LivingTickEvent event) {
        Entity entity = event.getEntity();
        if (!(entity instanceof Villager worker) || worker.level().isClientSide()
                || worker.tickCount % InferenceCadenceV02.DEFAULT_INTERVAL_TICKS != 0
                || !enabled(worker) || !(worker.level() instanceof ServerLevel level)) return;
        CompoundTag data = worker.getPersistentData();
        if (!data.contains(ORDER, 10)) return;
        CompoundTag order = data.getCompound(ORDER);
        boolean active = data.contains("HearthboundHaul", 10)
                || data.getBoolean("HearthboundTravelActive");
        boolean terminal = "TARGET_REACHED".equals(order.getString("State"));
        long now = level.getGameTime();
        long last = data.contains(LAST_TICK) ? data.getLong(LAST_TICK) : -1;
        if (!InferenceCadenceV02.shouldRun(now, last,
                InferenceCadenceV02.DEFAULT_INTERVAL_TICKS, active, terminal)) return;

        MillObservation observation;
        try {
            observation = MinecraftMillObservationAdapter.observe(worker);
        } catch (IllegalArgumentException unavailable) {
            return;
        }
        PolicyDecisionV02 decision = PolicyDecisionV02.from(observation, POLICY);
        MinecraftMillActionExecutor.Result result =
                MinecraftMillActionExecutor.execute(worker, decision);
        data.putLong(LAST_TICK, now);
        record(worker.getUUID(), observation, decision, result);
    }

    private static void record(UUID worker, MillObservation observation,
            PolicyDecisionV02 decision, MinecraftMillActionExecutor.Result result) {
        String json = "{\"schema\":\"" + VERSION + "\",\"worker\":\"" + worker
                + "\",\"world_version\":" + observation.step()
                + ",\"observation\":\"" + Arrays.toString(MillObservationEncoder.encode(observation))
                + "\",\"action\":\"" + decision.action().name()
                + "\",\"outcome\":\"" + result.outcome().name()
                + "\",\"accepted\":" + result.accepted() + "}";
        ArrayDeque<String> traces = TRACES.computeIfAbsent(worker, ignored -> new ArrayDeque<>());
        if (traces.size() >= TRACE_LIMIT) traces.removeFirst();
        traces.addLast(json);
        LOGGER.info("HB_AGENT_TRACE {}", json);
    }

    private static Villager nearestOrder(CommandSourceStack source) {
        return SableSelection.nearest(source,
                worker -> worker.getPersistentData().contains(ORDER, 10));
    }

    private static int fail(CommandSourceStack source, String message) {
        source.sendFailure(Component.literal(message));
        return 0;
    }
}
