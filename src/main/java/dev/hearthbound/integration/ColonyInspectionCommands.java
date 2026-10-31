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
        var entries = CitizenRegistrySavedData.get(ctx.getSource().getServer()).snapshot();
        ctx.getSource().sendSuccess(() -> Component.literal(
                "Hearthbound persisted citizen records=" + entries.size()
                + " (not spawned or autonomous entities)"), false);
        entries.stream().limit(12).forEach(citizen ->
                ctx.getSource().sendSuccess(() -> Component.literal(
                        citizen.name() + " id=" + citizen.id() + " task=" + citizen.task()
                        + " dimension=" + citizen.dimension()
                        + " pos=" + net.minecraft.core.BlockPos.of(citizen.position())), false));
        return entries.size();
    }
    public static int tasks(CommandContext<CommandSourceStack> ctx) {
        var entries = CitizenRegistrySavedData.get(ctx.getSource().getServer()).snapshot();
        long active = entries.stream().filter(citizen -> !"IDLE".equals(citizen.task())).count();
        ctx.getSource().sendSuccess(() -> Component.literal(
                "Hearthbound active persisted citizen tasks=" + active
                + "; autonomous world task execution not installed."), false);
        return (int) active;
    }
}
