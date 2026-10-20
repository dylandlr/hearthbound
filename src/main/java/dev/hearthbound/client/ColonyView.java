package dev.hearthbound.client;

import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.Camera;
import dev.hearthbound.world.mixin.TacticalCameraAccessor;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.client.event.InputEvent;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;
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
    private static final KeyMapping PAN_NORTH = new KeyMapping("key.hearthbound.pan_north", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_UP, "key.categories.hearthbound");
    private static final KeyMapping PAN_SOUTH = new KeyMapping("key.hearthbound.pan_south", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_DOWN, "key.categories.hearthbound");
    private static final KeyMapping PAN_WEST = new KeyMapping("key.hearthbound.pan_west", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_LEFT, "key.categories.hearthbound");
    private static final KeyMapping PAN_EAST = new KeyMapping("key.hearthbound.pan_east", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_RIGHT, "key.categories.hearthbound");
    private static final KeyMapping RESET_CAMERA = new KeyMapping("key.hearthbound.reset_camera", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_HOME, "key.categories.hearthbound");
    private static double panX = 0;
    private static double panZ = 0;
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
            event.register(PAN_NORTH);
            event.register(PAN_SOUTH);
            event.register(PAN_WEST);
            event.register(PAN_EAST);
            event.register(RESET_CAMERA);
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
            panX = 0;
            panZ = 0;
            return;
        }
        while (VIEW.consumeClick()) tactical = !tactical;
        while (ZOOM_IN.consumeClick()) if (tactical) cameraHeight = Math.max(8, cameraHeight - 3);
        while (ZOOM_OUT.consumeClick()) if (tactical) cameraHeight = Math.min(48, cameraHeight + 3);
        while (FOLLOW.consumeClick()) follow = !follow;
        while (RESET_CAMERA.consumeClick()) { panX = 0; panZ = 0; follow = false; }
        if (tactical && mc.screen == null) {
            double speed = .28 * (cameraHeight / 18.0);
            if (PAN_NORTH.isDown()) { panZ -= speed; follow = false; }
            if (PAN_SOUTH.isDown()) { panZ += speed; follow = false; }
            if (PAN_WEST.isDown()) { panX -= speed; follow = false; }
            if (PAN_EAST.isDown()) { panX += speed; follow = false; }
        }
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

    /** Center-screen camera ray selection, never authorizes commands on the server. */
    @SubscribeEvent
    public static void selectWithMouse(InputEvent.MouseButton.Pre event) {
        Minecraft mc = Minecraft.getInstance();
        if (!tactical || mc.screen != null || mc.level == null || mc.player == null
                || event.getButton() != GLFW.GLFW_MOUSE_BUTTON_LEFT
                || event.getAction() != GLFW.GLFW_PRESS) return;
        // In the initial mouse-locked prototype the cursor is the screen reticle.
        // A later RTS mouse-unlock pass will cast through the actual cursor pixel.
        Camera camera = mc.gameRenderer.getMainCamera();
        Vec3 start = camera.getPosition();
        Vector3f facing = camera.getLookVector();
        Vec3 end = start.add(facing.x() * 80, facing.y() * 80, facing.z() * 80);
        Villager nearest = null;
        double best = Double.MAX_VALUE;
        for (Villager citizen : mc.level.getEntitiesOfClass(Villager.class,
                new AABB(start, end).inflate(2))) {
            var hit = citizen.getBoundingBox().inflate(.5).clip(start, end);
            if (hit.isPresent()) {
                double distance = start.distanceToSqr(hit.get());
                if (distance < best) { best = distance; nearest = citizen; }
            }
        }
        if (nearest != null) {
            selected = nearest;
            event.setCanceled(true);
        }
    }

    @SubscribeEvent
    public static void camera(ViewportEvent.ComputeCameraAngles event) {
        if (!tactical) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.level == null) return;
        Camera camera = event.getCamera();
        // Presentation-only overhead framing. No client or server player movement.
        boolean tracking = follow && selected != null;
        double x = tracking ? selected.getX() : mc.player.getX() + panX;
        double y = tracking ? selected.getEyeY() : mc.player.getEyeY();
        double z = tracking ? selected.getZ() : mc.player.getZ() + panZ;
        ((TacticalCameraAccessor) camera).hearthbound$setPosition(x, y + cameraHeight, z + cameraHeight * .38);
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
        graphics.drawString(mc.font, "[I] Inspect [F] Follow [Arrows] Pan [Home] Reset [[] []] Zoom: "
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
