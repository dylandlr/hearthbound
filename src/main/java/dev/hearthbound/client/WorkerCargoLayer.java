package dev.hearthbound.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.model.VillagerModel;
import net.minecraft.client.renderer.ItemInHandRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;

/** A visual at the vanilla crossed-arm carrying position. No server equipment or drops. */
public final class WorkerCargoLayer extends RenderLayer<Villager, VillagerModel<Villager>> {
    private final ItemInHandRenderer items;

    public WorkerCargoLayer(RenderLayerParent<Villager, VillagerModel<Villager>> parent, ItemInHandRenderer items) {
        super(parent);
        this.items = items;
    }

    @Override
    public void render(PoseStack pose, MultiBufferSource buffers, int light, Villager worker,
            float walk, float walkAmount, float partialTick, float age, float yaw, float pitch) {
        var view = ClientWorkerViews.get(worker);
        if (view == null || view.cargo() <= 0 || worker.isInvisible()) return;
        ResourceLocation itemId = ResourceLocation.tryParse(view.item());
        if (itemId == null) return;
        // Temporary client render value only; authoritative count stays in HearthboundHaul.
        ItemStack visual = new ItemStack(BuiltInRegistries.ITEM.get(itemId));
        if (visual.isEmpty()) return;
        pose.pushPose();
        pose.translate(0, .4F, -.4F);
        if (view.activity().equals("putting_down")) {
            float reach = ClientWorkerViews.interactionProgress(worker, partialTick);
            pose.translate(0, .12F * reach, -.18F * reach);
        }
        pose.mulPose(Axis.XP.rotationDegrees(180));
        items.renderItem(worker, visual, ItemDisplayContext.GROUND, false, pose, buffers, light);
        pose.popPose();
        ClientWorkerViews.cargoRendered(worker);
    }
}
