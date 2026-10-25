package dev.hearthbound.integration;

import com.mojang.brigadier.context.CommandContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.network.chat.Component;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.server.MinecraftServer;
import java.util.Comparator;
import java.util.List;

/** Server-owned, read-only diagnostics; no fabricated NPC or task state. */
public final class ColonyInspectionCommands {
    private ColonyInspectionCommands() {}
    public static int observations(CommandContext<CommandSourceStack> ctx) {
        MinecraftServer server = ctx.getSource().getServer();
        ListTag history = MillingObservationSavedData.get(server).snapshot();
        int count = history.size();
        var source = ctx.getSource();
        source.sendSuccess(() -> Component.literal("Hearthbound actual Create milling observations=" + count
                + " (SavedData diagnostic journal; not autonomous citizen work)"), false);
        List<CompoundTag> records = new java.util.ArrayList<>();
        for (int i=0;i<count;i++) records.add(history.getCompound(i));
        records.sort(Comparator.comparingLong((CompoundTag record)->record.getLong("Tick")).reversed());
        records.stream().limit(8).forEach(record ->
                source.sendSuccess(() -> Component.literal("tick=" + record.getLong("Tick")
                        + " dimension=" + record.getString("Dimension")
                        + " pos=" + net.minecraft.core.BlockPos.of(record.getLong("Position"))
                        + " recipe=" + record.getString("Recipe")
                        + " quality=" + record.getString("Quality")
                        + " observation=" + record.getUUID("Id")), false));
        return count;
    }
    public static int citizens(CommandContext<CommandSourceStack> ctx) {
        ctx.getSource().sendSuccess(() -> Component.literal(
                "Hearthbound live autonomous citizens=0; server-side NPC registry not installed. "
                + "GameTest citizen IDs and credit fixtures are NOT live entities."), false);
        return 1;
    }
    public static int tasks(CommandContext<CommandSourceStack> ctx) {
        ctx.getSource().sendSuccess(() -> Component.literal(
                "Hearthbound live citizen tasks=0; persistent server task scheduler not installed. "
                + "Fixture work orders are not active colony tasks."), false);
        return 1;
    }
}
