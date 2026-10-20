package dev.hearthbound.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Vector3f;
import org.joml.Vector4f;

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
        // Only draw client-loaded entities within the local player's observation radius.
        // A future server-authorized visibility feed must replace this restriction.
        for (Villager citizen : mc.level.getEntitiesOfClass(Villager.class,
                mc.player.getBoundingBox().inflate(28))) {
            if (!citizen.isAlive()) continue;
            // Temporary compact roster rather than a world-space x-ray label.
            // World-space markers will require a rendering projection and permissions.
            // Deliberately avoid displaying coordinates for hidden enemies.
        }
        Villager selected = ColonyView.selectedCitizen();
        if (selected == null) return;
        int width = mc.getWindow().getGuiScaledWidth();
        int x = Math.max(10, width - 195);
        gfx.fill(x - 5, 28, width - 5, 93, 0xB70B1720);
        gfx.drawString(mc.font, "SELECTED CITIZEN", x, 34, 0xEAD8AD, false);
        gfx.drawString(mc.font, selected.getName().getString(), x, 47, 0xFFFFFF, false);
        gfx.drawString(mc.font, "Position: " + selected.blockPosition().toShortString(), x, 60, 0xC6DBDC, false);
        gfx.drawString(mc.font, "Health: " + (int) selected.getHealth(), x, 73, 0xC6DBDC, false);
    }
}
