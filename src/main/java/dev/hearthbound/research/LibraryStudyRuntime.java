package dev.hearthbound.research;

import java.util.Objects;
import dev.hearthbound.world.SableHauling;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BlockEntity;

/**
 * Server-only physical library study task, persisted on the citizen.
 *
 * A session advances only while the citizen is adjacent to the SAME loaded
 * book container, holds no competing session, and the registered book stays
 * physically present. No client-provided book/access booleans are trusted.
 */
public final class LibraryStudyRuntime {
    private static final String KEY = "hearthbound.libraryStudyV1";
    public static final String BOOK = "minecraft:written_book";
    public static final String TOPIC = "hearthbound:basic_milling";
    public static final String RECIPE = "create:milling/wheat";
    private static final int REQUIRED_TICKS = 200;
    private static final int MIN_LITERACY = 20;

    public enum State { IDLE, STUDYING, COMPLETED, INTERRUPTED }

    private LibraryStudyRuntime() {}

    /** The first integration target is a chest/barrel holding a written book.
     * This does not yet parse Patchouli or Create Ponder pages. */
    public static void begin(ServerLevel level, Villager citizen, BlockPos library, int literacy) {
        Objects.requireNonNull(level);
        Objects.requireNonNull(citizen);
        Objects.requireNonNull(library);
        if (citizen.level() != level) throw new IllegalArgumentException("Citizen is in another level");
        if (literacy < MIN_LITERACY || literacy > 100)
            throw new IllegalArgumentException("Literacy not sufficient");
        if (SableHauling.active(citizen))
            throw new IllegalStateException("Citizen is already hauling");
        if (state(citizen) == State.STUDYING)
            throw new IllegalStateException("Citizen already studying");
        if (!withinReach(citizen, library) || !hasBook(level, library))
            throw new IllegalStateException("No accessible physical book");

        CompoundTag data = new CompoundTag();
        data.putUUID("session", UUID.randomUUID());
        data.putString("dimension", level.dimension().location().toString());
        data.putLong("library", library.asLong());
        data.putInt("literacy", literacy);
        data.putLong("startTick", level.getGameTime());
        data.putInt("progress", 0);
        data.putLong("lastProgressTick", Long.MIN_VALUE);
        data.putString("state", State.STUDYING.name());
        citizen.getPersistentData().put(KEY, data);
    }

    /** Call from the server villager tick event. Interruption requires a new
     * session; elapsed wall-clock time or skipped server ticks never count. */
    public static void tick(ServerLevel level, Villager citizen) {
        CompoundTag data = citizen.getPersistentData().getCompound(KEY);
        if (!State.STUDYING.name().equals(data.getString("state"))) return;
        // Idempotent against multiple tick event subscriptions in one game tick.
        long gameTick = level.getGameTime();
        if (data.contains("lastProgressTick")
                && data.getLong("lastProgressTick") == gameTick) return;
        BlockPos pos = BlockPos.of(data.getLong("library"));
        if (!level.dimension().location().toString().equals(data.getString("dimension"))
                || !withinReach(citizen, pos) || !hasBook(level, pos)) {
            data.putString("state", State.INTERRUPTED.name());
            return;
        }
        data.putLong("lastProgressTick", gameTick);
        int progress = data.getInt("progress") + 1;
        data.putInt("progress", progress);
        if (progress < REQUIRED_TICKS) return;
        // Recheck the live physical inventory at the moment knowledge is awarded.
        if (!hasBook(level, pos)) {
            data.putString("state", State.INTERRUPTED.name());
            return;
        }
        CitizenTechnologyKnowledge.study(
                citizen, RECIPE, BOOK,
                data.getInt("literacy") / 100.0,
                level.getGameTime());
        data.putString("state", State.COMPLETED.name());
    }

    public static State state(Villager citizen) {
        String value = citizen.getPersistentData().getCompound(KEY).getString("state");
        if (value.isEmpty()) return State.IDLE;
        try { return State.valueOf(value); }
        catch (IllegalArgumentException ex) { return State.INTERRUPTED; }
    }

    public static String inspect(Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        return "LIBRARY_STUDY " + state(citizen)
                + " progress=" + tag.getInt("progress") + "/" + REQUIRED_TICKS
                + " library=" + BlockPos.of(tag.getLong("library"))
                + " recipe=" + RECIPE;
    }

    private static boolean withinReach(Villager citizen, BlockPos pos) {
        return citizen.distanceToSqr(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5) <= 9.0;
    }

    public static boolean hasBook(ServerLevel level, BlockPos pos) {
        if (!level.hasChunkAt(pos)) return false;
        BlockEntity entity = level.getBlockEntity(pos);
        if (!(entity instanceof Container inventory)) return false;
        for (int slot = 0; slot < inventory.getContainerSize(); slot++) {
            ItemStack stack = inventory.getItem(slot);
            if (!stack.isEmpty()
                    && BOOK.equals(BuiltInRegistries.ITEM.getKey(stack.getItem()).toString())
                    && stack.hasTag()
                    && "hearthbound:basic_milling".equals(stack.getTag().getString("hearthbound.lesson")))
                return true;
        }
        return false;
    }
}
