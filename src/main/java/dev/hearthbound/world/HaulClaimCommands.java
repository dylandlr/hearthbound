package dev.hearthbound.world;

import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.util.UUID;

/** Operator observability and explicitly owner-checked manual claim repair. */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class HaulClaimCommands {
    private HaulClaimCommands() {}

    @SubscribeEvent
    public static void onRegisterCommands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("hearthboundclaims")
            .requires(source -> source.hasPermission(2))
            .then(Commands.literal("count").executes(ctx -> {
                CommandSourceStack source = ctx.getSource();
                int total = HaulClaims.count(source.getLevel());
                source.sendSuccess(() -> Component.literal("Active source claims in this dimension: " + total), false);
                return total + 1;
            }))
            .then(Commands.literal("owner")
                .then(Commands.argument("source", BlockPosArgument.blockPos()).executes(ctx -> {
                    CommandSourceStack source = ctx.getSource();
                    BlockPos pos = BlockPosArgument.getLoadedBlockPos(ctx, "source");
                    UUID owner = HaulClaims.owner(source.getLevel(), pos);
                    source.sendSuccess(() -> Component.literal(owner == null
                        ? "No source claim at " + pos.toShortString()
                        : "Claim at " + pos.toShortString() + " belongs to " + owner), false);
                    return 1;
                })))
            .then(Commands.literal("release")
                .then(Commands.argument("source", BlockPosArgument.blockPos())
                    .then(Commands.argument("expectedOwner", StringArgumentType.word()).executes(ctx -> {
                        CommandSourceStack source = ctx.getSource();
                        BlockPos pos = BlockPosArgument.getLoadedBlockPos(ctx, "source");
                        UUID expected;
                        try {
                            expected = UUID.fromString(StringArgumentType.getString(ctx, "expectedOwner"));
                        } catch (IllegalArgumentException ex) {
                            source.sendFailure(Component.literal("Expected a full owner UUID."));
                            return 0;
                        }
                        if (!HaulClaims.releaseIfOwned(source.getLevel(), pos, expected)) {
                            source.sendFailure(Component.literal(
                                "Claim not released: missing claim or owner mismatch."));
                            return 0;
                        }
                        source.sendSuccess(() -> Component.literal(
                            "Source claim released. Inspect citizen cargo and chests before reassigning."), true);
                        return 1;
                    })))));
    }
}
