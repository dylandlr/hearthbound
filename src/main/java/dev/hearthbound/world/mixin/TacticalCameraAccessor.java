package dev.hearthbound.world.mixin;

import net.minecraft.client.Camera;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

/** Client-only bridge to Minecraft's protected camera positioning method. */
@Mixin(Camera.class)
public interface TacticalCameraAccessor {
    @Invoker("setPosition")
    void hearthbound$setPosition(double x, double y, double z);
}
