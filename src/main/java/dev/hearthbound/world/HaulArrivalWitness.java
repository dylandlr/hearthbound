package dev.hearthbound.world;

import com.google.gson.JsonArray;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import dev.hearthbound.evidence.HaulArrivalGeometry;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;

/**
 * Native observations at an insertion, plus a distinct later observation.
 * One bounded record in the current job, fenced by the existing server session.
 * This is neither a durable transaction journal nor a reward/completion gate.
 * Only local vanilla container NBT is inspected; no capability is queried.
 */
public final class HaulArrivalWitness {
    private static final String HAUL = "hearthbound.haul";
    private static final String RECORD = "arrivalWitness.v1";
    private static final String WORLD = "arrivalWorld";
    private static final String SESSION = "arrivalSession";
    private static final String DIMENSION = "arrivalDimension";
    private static final int MAX_RECORD_BYTES = 3000;
    private static final int MAX_REPLY_BYTES = 3900;
    public static final String PREFIX = "HAUL_ARRIVAL_V1 ";
    private HaulArrivalWitness() {}

    static void assigned(ServerLevel level, CompoundTag tag) {
        // Observation failure must not change the motor or create new authority.
        // A missing binding remains an explicit failure at the acceptance gate.
        try {
            UUID world = HearthboundWorldIdentity.peek(level);
            UUID session = SourceReportSession.peekEpisode(level);
            if (world != null && session != null) {
                tag.putUUID(WORLD, world);
                tag.putUUID(SESSION, session);
                tag.putString(DIMENSION, level.dimension().location().toString());
            }
        } catch (RuntimeException unavailable) {
            tag.remove(WORLD); tag.remove(SESSION); tag.remove(DIMENSION);
        }
    }

    private static JsonObject binding(Villager citizen, CompoundTag tag) {
        if (!tag.hasUUID("jobId") || !tag.hasUUID(WORLD) || !tag.hasUUID(SESSION)
                || !tag.contains(DIMENSION, Tag.TAG_STRING)
                || !tag.contains("source", Tag.TAG_LONG)
                || !tag.contains("destination", Tag.TAG_LONG)
                || !tag.contains("assignedTick", Tag.TAG_LONG))
            throw new IllegalStateException("Assignment binding unavailable");
        JsonObject value = new JsonObject();
        value.addProperty("world", tag.getUUID(WORLD).toString());
        value.addProperty("session", tag.getUUID(SESSION).toString());
        value.addProperty("dimension", tag.getString(DIMENSION));
        value.addProperty("citizen", citizen.getUUID().toString());
        value.addProperty("job", tag.getUUID("jobId").toString());
        value.addProperty("assigned_tick", tag.getLong("assignedTick"));
        value.add("source", position(BlockPos.of(tag.getLong("source"))));
        value.add("destination", position(BlockPos.of(tag.getLong("destination"))));
        return value;
    }

    private static JsonObject sample(ServerLevel level, Villager citizen, CompoundTag tag) {
        BlockPos source = BlockPos.of(tag.getLong("source"));
        BlockPos destination = BlockPos.of(tag.getLong("destination"));
        var pose = citizen.position();
        JsonObject value = new JsonObject();
        value.addProperty("tick", level.getGameTime());
        JsonArray position = new JsonArray();
        position.add(citizen.getX()); position.add(citizen.getY()); position.add(citizen.getZ());
        value.add("position", position);
        var distances = HaulArrivalGeometry.measure(citizen.getX(), citizen.getY(), citizen.getZ(),
            destination.getX(), destination.getY(), destination.getZ());
        value.addProperty("motor_distance_sq", distances.motor());
        value.addProperty("smoke_distance_sq", distances.smoke());
        value.add("source", HaulMotorDiagnostics.inventory(level, source));
        value.add("destination", HaulMotorDiagnostics.inventory(level, destination));
        if (!pose.equals(citizen.position()))
            throw new IllegalStateException("Native inventory read changed citizen position");
        return value;
    }

    static JsonObject beforeInsertion(ServerLevel level, Villager citizen, CompoundTag tag) {
        JsonObject observation = new JsonObject();
        try {
            observation.add("binding", binding(citizen, tag));
            observation.add("before", sample(level, citizen, tag));
            ItemStack cargo = ItemStack.of(tag.getCompound("cargo"));
            JsonObject item = new JsonObject();
            item.addProperty("item", net.minecraft.core.registries.BuiltInRegistries.ITEM
                .getKey(cargo.getItem()).toString());
            item.addProperty("count", cargo.getCount());
            observation.add("cargo", item);
            observation.addProperty("status", "OBSERVED");
        } catch (RuntimeException unavailable) {
            observation.addProperty("status", "UNAVAILABLE");
            observation.addProperty("error_type", unavailable.getClass().getSimpleName());
        }
        return observation;
    }

    static void afterInsertion(ServerLevel level, Villager citizen, CompoundTag tag,
                               JsonObject observation) {
        // Called even when the motor threw. Capture never retries insertion,
        // authorizes completion, or throws a new RuntimeException after it.
        try {
            observation.add("after", sample(level, citizen, tag));
            String encoded = observation.toString();
            if (encoded.getBytes(StandardCharsets.UTF_8).length > MAX_RECORD_BYTES)
                throw new IllegalStateException("Arrival observation exceeds record bound");
            tag.putString(RECORD, encoded);
        } catch (RuntimeException unavailable) {
            JsonObject failed = new JsonObject();
            failed.addProperty("status", "UNAVAILABLE");
            failed.addProperty("error_type", unavailable.getClass().getSimpleName());
            tag.putString(RECORD, failed.toString());
        }
    }

    public static JsonObject inspect(ServerLevel level, UUID id) {
        if (!level.getServer().isSameThread())
            throw new IllegalStateException("Arrival inspection requires the server thread");
        JsonObject result = new JsonObject();
        result.addProperty("schema", "hearthbound.haul-arrival.v1");
        result.addProperty("status", "UNAVAILABLE");
        result.addProperty("citizen", id.toString());
        result.addProperty("tick", level.getGameTime());
        result.addProperty("dimension", level.dimension().location().toString());
        result.addProperty("observation_scope", "LOCAL_VANILLA_CONTAINER_NBT");
        result.addProperty("reward_authorized", false);
        result.add("witness", JsonNull.INSTANCE);
        try {
            UUID world = HearthboundWorldIdentity.peek(level);
            UUID session = SourceReportSession.peekEpisode(level);
            if (world == null || session == null)
                throw new IllegalStateException("Current world/session unavailable");
            result.addProperty("world", world.toString());
            result.addProperty("session", session.toString());
            if (!(level.getEntity(id) instanceof Villager citizen))
                throw new IllegalStateException("Exact marked citizen unavailable");
            CompoundTag serialized = citizen.saveWithoutId(new CompoundTag()).getCompound("ForgeData");
            if (!serialized.getBoolean("hearthbound.sable")
                    && !serialized.getBoolean("hearthbound.citizen"))
                throw new IllegalStateException("Exact marked citizen unavailable");
            CompoundTag tag = citizen.getPersistentData().getCompound(HAUL);
            CompoundTag before = citizen.getPersistentData().copy();
            result.add("binding", binding(citizen, tag));
            if (!tag.contains("phase", Tag.TAG_INT))
                throw new IllegalStateException("Invalid job phase");
            result.addProperty("phase", tag.getInt("phase"));
            result.addProperty("cargo_present", tag.contains("cargo"));
            if (tag.contains("physicalDeliveredTick", Tag.TAG_LONG))
                result.addProperty("delivered_tick", tag.getLong("physicalDeliveredTick"));
            else result.add("delivered_tick", JsonNull.INSTANCE);
            result.add("current", sample(level, citizen, tag));
            if (tag.contains(RECORD)) {
                if (!tag.contains(RECORD, Tag.TAG_STRING)
                        || tag.getString(RECORD).getBytes(StandardCharsets.UTF_8).length > MAX_RECORD_BYTES)
                    throw new IllegalStateException("Malformed arrival observation");
                result.add("witness", JsonParser.parseString(tag.getString(RECORD)));
            }
            if (!before.equals(citizen.getPersistentData()))
                throw new IllegalStateException("Native read changed citizen state");
            result.addProperty("status", "OBSERVED");
        } catch (RuntimeException unavailable) {
            result.addProperty("status", "UNAVAILABLE");
            result.addProperty("error_type", unavailable.getClass().getSimpleName());
        }
        return result;
    }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(Commands.literal("hearthbound-haul-arrival")
            .requires(source -> source.hasPermission(2))
            .then(Commands.argument("citizen", StringArgumentType.word()).executes(ctx -> {
                UUID citizen;
                try {
                    String raw = StringArgumentType.getString(ctx, "citizen");
                    citizen = UUID.fromString(raw);
                    if (!citizen.toString().equals(raw)) throw new IllegalArgumentException();
                } catch (IllegalArgumentException invalid) {
                    ctx.getSource().sendFailure(Component.literal("Invalid canonical citizen UUID"));
                    return 0;
                }
                JsonObject snapshot = inspect(ctx.getSource().getLevel(), citizen);
                String encoded = PREFIX + snapshot;
                if (encoded.getBytes(StandardCharsets.UTF_8).length + 1 > MAX_REPLY_BYTES) {
                    snapshot = new JsonObject();
                    snapshot.addProperty("schema", "hearthbound.haul-arrival.v1");
                    snapshot.addProperty("status", "OVERSIZED_UNAVAILABLE");
                    encoded = PREFIX + snapshot;
                }
                final String reply = encoded;
                ctx.getSource().sendSuccess(() -> Component.literal(reply), false);
                return snapshot.get("status").getAsString().equals("OBSERVED") ? 1 : 0;
            })));
    }

    private static JsonArray position(BlockPos value) {
        JsonArray result = new JsonArray();
        result.add(value.getX()); result.add(value.getY()); result.add(value.getZ());
        return result;
    }
}
