package dev.hearthbound.client;

import java.util.ArrayList;
import dev.hearthbound.HearthboundMod;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Read-only worker card, shown while looking at a nearby colony citizen. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID, value = Dist.CLIENT)
public final class WorkerHud {
    private WorkerHud() {}

    @SubscribeEvent
    public static void render(RenderGuiEvent.Post event) {
        var mc = Minecraft.getInstance();
        if (mc.player == null || mc.screen != null || mc.options.hideGui
                || !(mc.hitResult instanceof EntityHitResult hit)
                || !(hit.getEntity() instanceof Villager worker) || mc.player.distanceToSqr(worker) > 144) return;
        var view = ClientWorkerViews.get(worker);
        if (view == null) return;
        var lines = new ArrayList<Component>();
        lines.add(worker.getDisplayName());
        lines.add(Component.translatable("hearthbound.activity." + view.activity()));
        if (view.cargo() > 0) {
            ResourceLocation id = ResourceLocation.tryParse(view.item());
            if (id != null) lines.add(Component.translatable("hearthbound.cargo", view.cargo(),
                    new ItemStack(BuiltInRegistries.ITEM.get(id)).getHoverName()));
        }
        if (view.hasOrder()) lines.add(view.stockedFlour() < 0
                ? Component.translatable("hearthbound.stock_unavailable")
                : view.targetFlour() > 0
                ? Component.translatable("hearthbound.stock_target", view.stockedFlour(), view.targetFlour())
                : Component.translatable("hearthbound.stock", view.stockedFlour()));
        int screenWidth = event.getWindow().getGuiScaledWidth();
        int width = Math.min(Math.min(280, screenWidth - 24),
                lines.stream().mapToInt(mc.font::width).max().orElse(120) + 24);
        boolean bar = view.hasOrder() && view.targetFlour() > 0 && view.stockedFlour() >= 0;
        int height = 16 + lines.size() * 12 + (bar ? 10 : 0);
        int x = 12, y = Math.max(8, event.getWindow().getGuiScaledHeight() - height - 48);
        var gui = event.getGuiGraphics();
        gui.fill(x, y, x + width, y + height, 0xED151B20);
        boolean blocked = switch (view.activity()) {
            case "paused", "output_full", "no_access", "missing_station" -> true;
            default -> false;
        };
        gui.fill(x, y, x + 3, y + height, blocked ? 0xFFFFBD66 : 0xFF75D8AE);
        for (int i = 0; i < lines.size(); i++) gui.drawString(mc.font,
                mc.font.plainSubstrByWidth(lines.get(i).getString(), width - 20), x + 10, y + 8 + i * 12,
                i == 0 ? 0xFFE7DFC5 : 0xFFF4F4F4, true);
        if (bar) {
            int bx = x + 10, by = y + height - 12, bw = width - 20;
            gui.fill(bx, by, bx + bw, by + 4, 0xFF414A4E);
            int filled = (int) (bw * Math.min(1.0, (double) view.stockedFlour() / view.targetFlour()));
            gui.fill(bx, by, bx + filled, by + 4, 0xFF75D8AE);
        }
        ClientWorkerViews.hudRendered(worker);
    }
}
