package dev.hearthbound.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * First real in-world roof mask visualization. The amber block outlines are
 * deliberately NOT transparent cutaways: the terrain rendering and server's
 * blocks remain unchanged. This diagnostic is limited to a selected villager.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", value = Dist.CLIENT)
public final class RoofCutawayDebugRenderer {
    private RoofCutawayDebugRenderer() {}

    @SubscribeEvent
    public static void render(RenderLevelStageEvent event) {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_TRANSLUCENT_BLOCKS
                || !ColonyView.isTactical() || !ColonyView.cutawayPreview()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null) return;
        Villager citizen = ColonyView.selectedCitizen();
        if (citizen == null || citizen.level() != mc.level || !citizen.isAlive()) return;
        var candidates = RoofCutawayMask.sample(mc.level, citizen.blockPosition(),
                ColonyView.observedFloorY(), 2, 16);
        if (candidates.isEmpty()) return;
        Vec3 camera = event.getCamera().getPosition();
        PoseStack pose = event.getPoseStack();
        VertexConsumer lines = mc.renderBuffers().bufferSource().getBuffer(RenderType.lines());
        // Keep debug outlines bounded so roofs cannot cause massive draw calls.
        int emitted = 0;
        for (BlockPos pos : candidates) {
            if (++emitted > 160) break;
            double x = pos.getX() - camera.x;
            double y = pos.getY() - camera.y;
            double z = pos.getZ() - camera.z;
            LevelRenderer.renderLineBox(pose, lines, x, y, z, x + 1, y + 1, z + 1,
                    0.96F, 0.72F, 0.28F, 0.82F);
        }
        mc.renderBuffers().bufferSource().endBatch(RenderType.lines());
    }
}
