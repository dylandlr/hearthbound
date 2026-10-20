package dev.hearthbound.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.Vec3;
import net.minecraft.client.Camera;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;
import org.joml.Vector3f;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * Client UI markers for loaded villagers in the tactical view.
 * Explicitly a prototype: no roof geometry removal or server-authorized
 * cross-team visibility is provided here.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", value = Dist.CLIENT)
public final class CitizenTacticalMarkers {
    private CitizenTacticalMarkers() {}

    @SubscribeEvent
    public static void render(RenderGuiEvent.Post event) {
        if (!ColonyView.isTactical()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null || mc.options.hideGui) return;
        GuiGraphics gfx = event.getGuiGraphics();
        Villager selected = ColonyView.selectedCitizen();
        if (selected == null) return;
        // Render only the selected, already-known citizen through occlusion.
        // This HUD projection works through roofs without editing the world,
        // but does not discover or reveal other hidden entities.
        Camera camera = mc.gameRenderer.getMainCamera();
        Vec3 displacement = selected.position().add(0, selected.getBbHeight() + .7, 0)
                .subtract(camera.getPosition());
        Vector3f look = camera.getLookVector();
        Vector3f left = camera.getLeftVector();
        Vector3f up = camera.getUpVector();
        double depth = displacement.x * look.x() + displacement.y * look.y() + displacement.z * look.z();
        if (depth > 0.2) {
            double fov = Math.tan(Math.toRadians(mc.options.fov().get()) * .5);
            double sx = displacement.x * left.x() + displacement.y * left.y() + displacement.z * left.z();
            double sy = displacement.x * up.x() + displacement.y * up.y() + displacement.z * up.z();
            int sw = mc.getWindow().getGuiScaledWidth();
            int sh = mc.getWindow().getGuiScaledHeight();
            int px = (int)Math.round(sw * .5 - sx / (depth * fov) * sh * .5);
            int py = (int)Math.round(sh * .5 - sy / (depth * fov) * sh * .5);
            if (px > 12 && px < sw - 12 && py > 12 && py < sh - 12) {
                gfx.fill(px - 4, py - 4, px + 5, py + 5, 0xFFE6C778);
                gfx.drawString(mc.font, selected.getName().getString(), px + 9, py - 4, 0xFFF6E7B7, true);
            }
        }
        int width = mc.getWindow().getGuiScaledWidth();
        int x = Math.max(10, width - 195);
        gfx.fill(x - 5, 28, width - 5, 120, 0xB70B1720);
        gfx.drawString(mc.font, "SELECTED CITIZEN", x, 34, 0xEAD8AD, false);
        gfx.drawString(mc.font, selected.getName().getString(), x, 47, 0xFFFFFF, false);
        gfx.drawString(mc.font, "Position: " + selected.blockPosition().toShortString(), x, 60, 0xC6DBDC, false);
        gfx.drawString(mc.font, "Health: " + (int) selected.getHealth(), x, 73, 0xC6DBDC, false);
        int floor = ColonyView.observedFloorY();
        int agentY = selected.blockPosition().getY();
        gfx.drawString(mc.font, "View Y: " + floor + "  Citizen Y: " + agentY, x, 86, 0xC6DBDC, false);
        int cover = ColonyView.cutawayPreview() ? solidCoverAbove(selected, Math.min(16, Math.max(0, floor - agentY))) : 0;
        gfx.drawString(mc.font, "Cutaway [C]: " + (ColonyView.cutawayPreview() ? "preview (" + cover + " solid)" : "off"), x, 99,
                cover > 0 ? 0xFFF1BD77 : 0xFF9EDDB8, false);
    }

    /** Count solid visual cover only in loaded chunks; never request or mutate chunks. */
    private static int solidCoverAbove(Villager citizen, int levels) {
        int total = 0;
        BlockPos foot = citizen.blockPosition();
        for (int offset = 2; offset <= levels; offset++) {
            BlockPos pos = foot.above(offset);
            if (!citizen.level().hasChunkAt(pos)) break;
            BlockState state = citizen.level().getBlockState(pos);
            if (state.canOcclude() && state.isSolidRender(citizen.level(), pos)) total++;
        }
        return total;
    }
}
