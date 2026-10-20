package dev.hearthbound.client;

import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.Camera;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.lwjgl.glfw.GLFW;

/**
 * Initial local tactical camera; never moves/teleports the server player.
 * Roof/cave occlusion rendering and mouse picking remain future work.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", value = Dist.CLIENT)
public final class ColonyView {
    private static final KeyMapping VIEW = new KeyMapping("key.hearthbound.view",
            InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_V, "key.categories.hearthbound");
    private static final KeyMapping INSPECT = new KeyMapping("key.hearthbound.inspect",
            InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_I, "key.categories.hearthbound");
    private static final KeyMapping ZOOM_IN = new KeyMapping("key.hearthbound.zoom_in",
            InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_LEFT_BRACKET, "key.categories.hearthbound");
    private static final KeyMapping ZOOM_OUT = new KeyMapping("key.hearthbound.zoom_out",
            InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_RIGHT_BRACKET, "key.categories.hearthbound");
    private static final KeyMapping FOLLOW = new KeyMapping("key.hearthbound.follow",
            InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_F, "key.categories.hearthbound");
    private static boolean tactical = true;
    private static boolean follow = false;
    private static double cameraHeight = 18;
    private static Villager selected;

    private ColonyView() {}

    @Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
    public static final class Keys {
        @SubscribeEvent
        public static void register(RegisterKeyMappingsEvent event) {
            event.register(VIEW);
            event.register(INSPECT);
            event.register(ZOOM_IN);
            event.register(ZOOM_OUT);
            event.register(FOLLOW);
        }
    }

    @SubscribeEvent
    public static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.level == null) {
            selected = null;
            tactical = true;
            follow = false;
            cameraHeight = 18;
            return;
        }
        while (VIEW.consumeClick()) tactical = !tactical;
        while (ZOOM_IN.consumeClick()) if (tactical) cameraHeight = Math.max(8, cameraHeight - 3);
        while (ZOOM_OUT.consumeClick()) if (tactical) cameraHeight = Math.min(48, cameraHeight + 3);
        while (FOLLOW.consumeClick()) follow = !follow;
        while (INSPECT.consumeClick()) {
            Villager nearest = null;
            double best = 24 * 24;
            for (Villager villager : mc.level.getEntitiesOfClass(Villager.class,
                    mc.player.getBoundingBox().inflate(24))) {
                double distance = villager.distanceToSqr(mc.player);
                if (distance < best) { best = distance; nearest = villager; }
            }
            selected = nearest;
        }
        if (selected != null && (!selected.isAlive() || selected.level() != mc.level))
            selected = null;
    }

    @SubscribeEvent
    public static void camera(ViewportEvent.ComputeCameraAngles event) {
        if (!tactical) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.level == null) return;
        Camera camera = event.getCamera();
        // Presentation-only overhead framing. No client or server player movement.
        boolean tracking = follow && selected != null;
        double x = tracking ? selected.getX() : mc.player.getX();
        double y = tracking ? selected.getEyeY() : mc.player.getEyeY();
        double z = tracking ? selected.getZ() : mc.player.getZ();
        camera.setPosition(x, y + cameraHeight, z + cameraHeight * .38);
        event.setYaw(0);
        event.setPitch(80);
        event.setRoll(0);
    }

    @SubscribeEvent
    public static void overlay(RenderGuiEvent.Post event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.options.hideGui) return;
        GuiGraphics graphics = event.getGuiGraphics();
        graphics.drawString(mc.font, tactical ? "HEARTHBOUND | Colony view [V: First person]"
                : "HEARTHBOUND | First person [V: Colony view]", 10, 10, 0xF1E8C9, true);
        graphics.drawString(mc.font, "[I] Inspect  [F] Follow  [[] []] Zoom: "
                + (int)cameraHeight + "  tracking=" + follow, 10, 22, 0xC5CECE, true);
        if (selected != null) {
            graphics.drawString(mc.font, "Citizen: " + selected.getName().getString(),
                    10, 38, 0xF1E8C9, true);
            graphics.drawString(mc.font, "Health: " + (int) selected.getHealth()
                    + "  Profession: " + selected.getVillagerData().getProfession(),
                    10, 50, 0xC5CECE, true);
        }
    }
}
