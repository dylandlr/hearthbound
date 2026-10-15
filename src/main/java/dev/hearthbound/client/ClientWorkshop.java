package dev.hearthbound.client;

import dev.hearthbound.HearthboundMod;
import dev.hearthbound.controls.WorkshopAction;
import dev.hearthbound.controls.WorkshopNetwork;
import dev.hearthbound.controls.WorkshopSnapshot;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.InputEvent;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.lwjgl.glfw.GLFW;

/** Unsaved world picks remain client-local until an explicit Start/Save. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID, value = Dist.CLIENT)
public final class ClientWorkshop {
    static final String[] KEYS = {"Wheat", "Mill", "Flour", "Wait"};
    static final String[] LABELS = {"Wheat barrel", "Millstone", "Flour barrel", "Waiting spot"};
    public static final class Draft {
        WorkshopSnapshot snapshot;
        final BlockPos[] points = new BlockPos[4];
        String target, notice = "";
        Draft(WorkshopSnapshot s) {
            snapshot = s;
            for (int i = 0; i < 4; i++) if (s.settings().contains(KEYS[i], 4)) points[i] = BlockPos.of(s.settings().getLong(KEYS[i]));
            target = Integer.toString(s.settings().getInt("TargetFlour"));
        }
        boolean ready() { return points[0] != null && points[1] != null && points[2] != null; }
        int amount() { try { return Integer.parseInt(target); } catch (NumberFormatException e) { return -1; } }
    }
    static Draft draft;
    static int selecting = -1;
    private static java.util.UUID opening;
    private static long consumeThroughTick = -1;
    private ClientWorkshop() {}

    public static void accept(WorkshopSnapshot snapshot) {
        var mc = Minecraft.getInstance();
        if (mc.level == null || !mc.level.dimension().location().equals(snapshot.worker().dimension())) return;
        if (draft == null && !snapshot.worker().workerId().equals(opening)) return;
        if (draft != null && !draft.snapshot.worker().workerId().equals(snapshot.worker().workerId())) return;
        boolean replace = draft == null || draft.snapshot.revision() != snapshot.revision();
        if (replace) draft = new Draft(snapshot); else draft.snapshot = snapshot;
        if (!snapshot.notice().isEmpty()) draft.notice = snapshot.notice();
        opening = null;
        log("SNAPSHOT order=" + snapshot.worker().view().hasOrder() + " editable=" + snapshot.canEdit()
                + " busy=" + snapshot.busy() + " revision=" + snapshot.revision() + " notice=" + snapshot.notice());
        if (selecting < 0 && !(mc.screen instanceof WorkshopStatusScreen) && !(mc.screen instanceof WorkshopSharingScreen)
                && (replace || !(mc.screen instanceof WorkerOrderScreen))) mc.setScreen(new WorkerOrderScreen());
    }

    static boolean validWorker() {
        var mc = Minecraft.getInstance();
        if (draft == null || mc.player == null || mc.level == null
                || !mc.level.dimension().location().equals(draft.snapshot.worker().dimension())) return false;
        var worker = mc.level.getEntity(draft.snapshot.worker().entityId());
        return worker != null && worker.isAlive() && worker.getUUID().equals(draft.snapshot.worker().workerId())
                && mc.player.distanceToSqr(worker) <= 32 * 32;
    }

    static void send(int action) {
        if (draft == null) return;
        var d = draft;
        WorkshopNetwork.CHANNEL.sendToServer(new WorkshopAction(d.snapshot.worker().workerId(), action,
                d.snapshot.revision(), d.points[0], d.points[1], d.points[2], d.points[3], d.amount(), null));
        if (action != WorkshopAction.REFRESH) log("ACTION action=" + action + " target=" + d.amount());
    }

    static void sendAccess(int action, java.util.UUID player) {
        if (draft == null) return;
        var d = draft;
        WorkshopNetwork.CHANNEL.sendToServer(new WorkshopAction(d.snapshot.worker().workerId(), action,
                d.snapshot.revision(), d.points[0], d.points[1], d.points[2], d.points[3], d.amount(), player));
        log("ACCESS_ACTION action=" + action + " player=" + player);
    }

    static void select(int slot) {
        if (draft == null) return;
        selecting = slot; draft.notice = "";
        Minecraft.getInstance().setScreen(null);
        log("SELECT kind=" + KEYS[slot]);
    }

    static void close() {
        send(WorkshopAction.CLOSE); draft = null; selecting = -1; opening = null;
        Minecraft.getInstance().setScreen(null);
    }

    static void log(String detail) {
        if (Boolean.getBoolean("hearthbound.recordWorkshopControls"))
            org.apache.logging.log4j.LogManager.getLogger().info("HB_WORKSHOP_" + detail);
    }

    @SubscribeEvent
    public static void use(InputEvent.InteractionKeyMappingTriggered event) {
        if (!event.isUseItem()) return;
        var mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null) return;
        if (mc.level.getGameTime() <= consumeThroughTick) { event.setCanceled(true); event.setSwingHand(false); return; }
        if (mc.screen != null) return;
        if (selecting >= 0 && draft != null) {
            event.setCanceled(true); event.setSwingHand(false);
            if (event.getHand() != InteractionHand.MAIN_HAND) return;
            consumeThroughTick = mc.level.getGameTime() + 2;
            if (!(mc.hitResult instanceof BlockHitResult hit)) { draft.notice = "Look at a workshop block."; return; }
            BlockPos point = hit.getBlockPos();
            String id = BuiltInRegistries.BLOCK.getKey(mc.level.getBlockState(point).getBlock()).toString();
            boolean valid = selecting == 3 ? hit.getDirection() == Direction.UP
                    : id.equals(selecting == 1 ? "create:millstone" : "minecraft:barrel");
            if (!valid) { draft.notice = selecting == 3 ? "Choose the top of a floor block." : "Choose a " + LABELS[selecting].toLowerCase() + "."; return; }
            if (selecting == 3) point = point.above();
            draft.points[selecting] = point.immutable();
            log("PICK kind=" + KEYS[selecting] + " point=" + point.toShortString());
            selecting = -1;
            send(WorkshopAction.REFRESH);
            mc.setScreen(new WorkerOrderScreen());
            return;
        }
        if (mc.player.getMainHandItem().isEmpty() && mc.hitResult instanceof EntityHitResult hit
                && hit.getEntity() instanceof Villager worker && ClientWorkerViews.get(worker) != null && ClientWorkerViews.get(worker).visible()) {
            event.setCanceled(true); event.setSwingHand(false);
            if (event.getHand() != InteractionHand.MAIN_HAND) return;
            consumeThroughTick = mc.level.getGameTime() + 2;
            draft = null; selecting = -1; opening = worker.getUUID();
            WorkshopNetwork.CHANNEL.sendToServer(new WorkshopAction(opening, WorkshopAction.OPEN, 0, null, null, null, null, 0, null));
        }
    }

    @SubscribeEvent
    public static void key(InputEvent.Key event) {
        if (selecting >= 0 && draft != null && event.getKey() == GLFW.GLFW_KEY_ESCAPE && event.getAction() == GLFW.GLFW_PRESS) {
            selecting = -1; Minecraft.getInstance().setScreen(new WorkerOrderScreen());
        }
    }

    @SubscribeEvent
    public static void selectionHud(RenderGuiEvent.Post event) {
        var mc = Minecraft.getInstance();
        if (selecting < 0 || draft == null || mc.screen != null || mc.options.hideGui) return;
        var gui = event.getGuiGraphics();
        String prompt = selecting == 3 ? "Right-click the top of a floor block" : "Right-click the " + LABELS[selecting].toLowerCase();
        int width = event.getWindow().getGuiScaledWidth(), y = event.getWindow().getGuiScaledHeight() - 75;
        gui.fill(10, y - 6, width - 10, y + 34, 0xED151B20);
        gui.drawCenteredString(mc.font, prompt, width / 2, y, 0xFFF4F4F4);
        gui.drawCenteredString(mc.font, draft.notice.isEmpty() ? "Esc: return to setup" : draft.notice, width / 2, y + 14, 0xFFFFBD66);
    }

    @SubscribeEvent
    public static void logout(ClientPlayerNetworkEvent.LoggingOut event) {
        draft = null; selecting = -1; opening = null; consumeThroughTick = -1;
    }
}
