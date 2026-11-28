package dev.hearthbound.world;

import com.google.gson.JsonArray;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import java.nio.charset.StandardCharsets;
import java.util.Objects;
import java.util.UUID;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.ai.navigation.PathNavigation;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.pathfinder.Node;
import net.minecraft.world.level.pathfinder.Path;
import net.minecraft.world.phys.Vec3;

/**
 * Permission-2 observations of an exact loaded citizen. This class never ticks
 * an actor, requests a path, resolves an item capability, or repairs authority.
 * Existing SavedData may be cached from disk, but missing stores are not created.
 * Native entity/container serialization can invoke vanilla or Forge hooks. The
 * named before/after checks below start after entity serialization and do not
 * establish that those hooks, the entire entity, or the whole world are pure.
 */
public final class HaulMotorDiagnostics {
    public static final String SCHEMA = "hearthbound.haul-motor-diagnostics.v1";
    public static final String PREFIX = "HAUL_MOTOR_DIAGNOSTICS_V1 ";
    private static final int MAX_REPLY_BYTES = 3900;
    private static final int MAX_SLOTS = 64;
    private static final int MAX_TEXT = 96;
    private static final String HAUL = "hearthbound.haul";
    private static final String PRIVATE_TRIAL = "hearthbound.private_communication_trial.v1";
    private static final double MOTOR_REACH_SQ = 6.25;

    private HaulMotorDiagnostics() {}

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(Commands.literal("hearthbound-haul-diagnostics")
            .requires(source -> source.hasPermission(2))
            .then(Commands.argument("citizen", StringArgumentType.word())
                .executes(ctx -> {
                    String raw = StringArgumentType.getString(ctx, "citizen");
                    UUID id;
                    try {
                        id = UUID.fromString(raw);
                        if (!id.toString().equalsIgnoreCase(raw))
                            throw new IllegalArgumentException("Noncanonical UUID");
                    } catch (IllegalArgumentException invalid) {
                        return reply(ctx.getSource(), common(ctx.getSource().getLevel(),
                            null, "INVALID_UUID"));
                    }
                    return reply(ctx.getSource(), inspect(ctx.getSource().getLevel(), id));
                })));
    }

    private static JsonObject common(ServerLevel level, UUID citizen, String status) {
        JsonObject root = new JsonObject();
        root.addProperty("schema", SCHEMA);
        root.addProperty("status", status);
        String dimension = level.dimension().location().toString();
        value(root, "dimension", dimension.length() <= MAX_TEXT ? dimension : null);
        root.addProperty("dimension_available", dimension.length() <= MAX_TEXT);
        root.addProperty("tick", level.getGameTime());
        value(root, "citizen", citizen == null ? null : citizen.toString());
        root.addProperty("loaded", false);
        root.addProperty("strictly_read_only", true);
        root.addProperty("atomic", true);
        root.addProperty("policy_control", false);
        root.addProperty("reward_authorized", false);
        try {
            UUID world = HearthboundWorldIdentity.peek(level);
            value(root, "world", world == null ? null : world.toString());
            root.addProperty("world_state", world == null ? "ABSENT" : "PRESENT");
        } catch (RuntimeException unavailable) {
            root.add("world", JsonNull.INSTANCE);
            root.addProperty("world_state", "UNAVAILABLE");
        }
        return root;
    }

    /** Caller must be on the authoritative server thread. */
    public static JsonObject inspect(ServerLevel level, UUID id) {
        if (!level.getServer().isSameThread())
            throw new IllegalStateException("Haul inspection requires the server thread");
        JsonObject root = common(level, id, "NOT_LOADED_IN_DIMENSION");
        Entity entity = level.getEntity(id);
        if (entity == null) return root;
        root.addProperty("loaded", true);
        root.addProperty("status", "NOT_A_MARKED_VILLAGER");
        if (!(entity instanceof Villager citizen)) return root;

        // Entity serialization reads ForgeData without calling getPersistentData
        // on an unmarked entity (that getter may allocate an empty compound).
        // Serialization hooks run before the following invariant baselines;
        // the checks therefore certify only the explicitly named later reads.
        CompoundTag serialized = citizen.saveWithoutId(new CompoundTag());
        CompoundTag before = serialized.getCompound("ForgeData").copy();
        boolean sable = before.getBoolean("hearthbound.sable");
        boolean marked = before.getBoolean("hearthbound.citizen");
        if (!sable && !marked) return root;
        CompoundTag tag = before.getCompound(HAUL);
        BlockPos source = position(tag, "source");
        BlockPos destination = position(tag, "destination");
        PathNavigation navigation = citizen.getNavigation();
        Path oldPath = navigation.getPath();
        int oldIndex = oldPath == null ? -1 : oldPath.getNextNodeIndex();
        Vec3 oldPosition = citizen.position();
        Vec3 oldVelocity = citizen.getDeltaMovement();
        boolean oldNoAi = citizen.isNoAi();
        int oldTickCount = citizen.tickCount;

        try {
            HaulClaims.Snapshot claim = HaulClaims.snapshot(level, source);
            root.addProperty("status", "OBSERVED");
            root.addProperty("observation_scope", "NAMED_MOTOR_AUTHORITY_INVARIANTS");
            root.addProperty("invariant_baseline", "AFTER_NATIVE_ENTITY_SERIALIZATION");
            JsonObject actor = new JsonObject();
            actor.addProperty("alive", citizen.isAlive());
            actor.addProperty("no_ai", citizen.isNoAi());
            actor.addProperty("can_update", citizen.canUpdate());
            actor.addProperty("tick_count", citizen.tickCount);
            actor.add("position", vector(citizen.position()));
            actor.add("velocity", vector(citizen.getDeltaMovement()));
            actor.addProperty("on_ground", citizen.onGround());
            actor.addProperty("horizontal_collision", citizen.horizontalCollision);
            JsonArray chunk = new JsonArray();
            chunk.add(citizen.chunkPosition().x); chunk.add(citizen.chunkPosition().z);
            actor.add("chunk", chunk);
            actor.addProperty("chunk_loaded", level.hasChunkAt(citizen.blockPosition()));
            actor.addProperty("forced_chunk", level.getForcedChunks().contains(citizen.chunkPosition().toLong()));
            actor.addProperty("position_entity_ticking", level.isPositionEntityTicking(citizen.blockPosition()));
            actor.addProperty("sable_marker", sable);
            actor.addProperty("citizen_marker", marked);
            actor.addProperty("private_trial_marker", before.getBoolean(PRIVATE_TRIAL));
            root.add("entity", actor);
            root.add("haul", haul(before, tag, source, destination));
            root.add("claim", claim(claim, source, id));
            root.add("motor", motor(level, citizen, tag, source, destination));
            root.add("navigation", navigation(navigation, oldPath));
            JsonObject inventories = new JsonObject();
            inventories.add("source", inventory(level, source));
            inventories.add("destination", inventory(level, destination));
            root.add("inventories", inventories);

            JsonObject checks = new JsonObject();
            checks.addProperty("persistent_nbt_unchanged", before.equals(citizen.getPersistentData()));
            checks.addProperty("path_identity_unchanged", navigation.getPath() == oldPath);
            checks.addProperty("path_index_unchanged", oldPath == null
                || oldPath.getNextNodeIndex() == oldIndex);
            checks.addProperty("claim_unchanged", claim.equals(HaulClaims.snapshot(level, source)));
            checks.addProperty("tick_count_unchanged", citizen.tickCount == oldTickCount);
            checks.addProperty("position_unchanged", oldPosition.equals(citizen.position()));
            checks.addProperty("velocity_unchanged", oldVelocity.equals(citizen.getDeltaMovement()));
            checks.addProperty("no_ai_unchanged", oldNoAi == citizen.isNoAi());
            root.add("read_only_checks", checks);
            if (checks.entrySet().stream().anyMatch(entry -> !entry.getValue().getAsBoolean())) {
                root.addProperty("status", "OBSERVATION_SIDE_EFFECT_DETECTED");
                root.addProperty("strictly_read_only", false);
            }
        } catch (RuntimeException unavailable) {
            root.addProperty("status", "SNAPSHOT_UNAVAILABLE");
            root.addProperty("error_type", shortText(unavailable.getClass().getSimpleName()));
        }
        return root;
    }

    private static JsonObject haul(CompoundTag persistent, CompoundTag tag,
                                   BlockPos source, BlockPos destination) {
        JsonObject row = new JsonObject();
        row.addProperty("present", persistent.contains(HAUL));
        row.addProperty("type", persistent.getTagType(HAUL));
        JsonObject types = new JsonObject();
        for (String key : new String[] {"phase", "source", "destination", "jobId",
                "colonyWorldId", "assignedTick", "physicalDeliveredTick", "cargo", "error"})
            types.addProperty(key, tag.getTagType(key));
        row.add("types", types);
        Integer phase = tag.contains("phase", Tag.TAG_INT) ? tag.getInt("phase") : null;
        value(row, "phase", phase);
        row.addProperty("phase_name", phaseName(phase));
        value(row, "job", tag.hasUUID("jobId") ? tag.getUUID("jobId").toString() : null);
        value(row, "world", tag.hasUUID("colonyWorldId") ? tag.getUUID("colonyWorldId").toString() : null);
        row.add("source", position(source)); row.add("destination", position(destination));
        value(row, "assigned_tick", typedLong(tag, "assignedTick"));
        value(row, "delivered_tick", typedLong(tag, "physicalDeliveredTick"));
        String error = tag.contains("error", Tag.TAG_STRING) ? tag.getString("error") : null;
        value(row, "error", error == null ? null : shortText(error));
        row.addProperty("error_truncated", error != null && error.length() > MAX_TEXT);
        JsonObject cargo = new JsonObject();
        cargo.addProperty("present", tag.contains("cargo"));
        cargo.addProperty("type", tag.getTagType("cargo"));
        CompoundTag item = tag.getCompound("cargo");
        String itemId = item.contains("id", Tag.TAG_STRING) ? item.getString("id") : null;
        Integer count = item.contains("Count", Tag.TAG_BYTE) ? (int)item.getByte("Count") : null;
        value(cargo, "item", itemId == null ? null : shortText(itemId));
        value(cargo, "count", count);
        value(cargo, "empty", itemId != null && count != null
            ? count <= 0 || itemId.equals("minecraft:air") : null);
        cargo.addProperty("item_truncated", itemId != null && itemId.length() > MAX_TEXT);
        row.add("cargo", cargo);
        return row;
    }

    private static JsonObject claim(HaulClaims.Snapshot snapshot, BlockPos source, UUID citizen) {
        JsonObject row = new JsonObject();
        row.addProperty("store_present", snapshot.storePresent());
        value(row, "source_owner", snapshot.sourceOwner() == null ? null : snapshot.sourceOwner().toString());
        value(row, "owned_by_citizen", snapshot.storePresent() && source != null
            ? citizen.equals(snapshot.sourceOwner()) : null);
        value(row, "total_claims", snapshot.storePresent() ? snapshot.totalClaims() : null);
        return row;
    }

    private static JsonObject motor(ServerLevel level, Villager citizen, CompoundTag tag,
                                    BlockPos source, BlockPos destination) {
        JsonObject row = new JsonObject();
        Integer phase = tag.contains("phase", Tag.TAG_INT) ? tag.getInt("phase") : null;
        BlockPos target = phase == null ? null : phase == 0 ? source : phase == 1 ? destination : null;
        row.addProperty("active", SableHauling.active(citizen));
        row.addProperty("phase_known", phase != null && phase >= 0 && phase <= 6);
        row.addProperty("paused", Objects.equals(phase, 3));
        row.addProperty("quarantined", Objects.equals(phase, 4));
        row.add("intended_target", position(target));
        row.addProperty("reach_sq", MOTOR_REACH_SQ);
        value(row, "target_chunk_loaded", target == null ? null : level.hasChunkAt(target));
        Vec3 distanceTarget = target == null ? null
            : new Vec3(target.getX() + .5, target.getY() + .5, target.getZ() + .5);
        Vec3 navigationTarget = target == null ? null
            : new Vec3(target.getX() + .5, target.getY(), target.getZ() + .5);
        row.add("distance_target", vector(distanceTarget));
        row.add("navigation_request_target", vector(navigationTarget));
        Double distance = distanceTarget == null ? null : citizen.position().distanceToSqr(distanceTarget);
        value(row, "distance_sq", distance);
        value(row, "within_reach", distance == null ? null : distance <= MOTOR_REACH_SQ);
        return row;
    }

    private static JsonObject navigation(PathNavigation navigation, Path path) {
        JsonObject row = new JsonObject();
        row.addProperty("done", navigation.isDone());
        row.addProperty("stuck", navigation.isStuck());
        row.add("target", position(navigation.getTargetPos()));
        row.addProperty("path_present", path != null);
        value(row, "next_node_index", path == null ? null : path.getNextNodeIndex());
        value(row, "node_count", path == null ? null : path.getNodeCount());
        value(row, "path_can_reach", path == null ? null : path.canReach());
        row.add("path_target", position(path == null ? null : path.getTarget()));
        int next = path == null ? -1 : path.getNextNodeIndex();
        row.add("next_node", node(path != null && next >= 0 && next < path.getNodeCount()
            ? path.getNode(next) : null));
        row.add("end_node", node(path == null ? null : path.getEndNode()));
        return row;
    }

    /** Reads native local Items without querying capability inventory or unpacking loot. */
    static JsonObject inventory(ServerLevel level, BlockPos position) {
        JsonObject row = new JsonObject();
        row.addProperty("status", "NO_ENDPOINT");
        row.addProperty("scope", "LOCAL_VANILLA_CONTAINER_NBT");
        value(row, "slots", null); value(row, "inspected_slots", null);
        value(row, "wheat", null); value(row, "total_items", null);
        row.addProperty("complete", false);
        if (position == null) return row;
        if (!level.hasChunkAt(position)) {
            row.addProperty("status", "CHUNK_UNLOADED"); return row;
        }
        BlockEntity block = level.getBlockEntity(position);
        if (block == null) { row.addProperty("status", "NO_BLOCK_ENTITY"); return row; }
        if (!(block instanceof Container container)
                || !BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(block.getType()).getNamespace().equals("minecraft")) {
            row.addProperty("status", "CAPABILITY_NOT_INSPECTED"); return row;
        }
        CompoundTag saved = block.saveWithoutMetadata();
        if (saved.contains("LootTable")) {
            row.addProperty("status", "LOOT_TABLE_NOT_REALIZED"); return row;
        }
        int slots = container.getContainerSize();
        if (slots < 0 || !saved.contains("Items", Tag.TAG_LIST)) {
            row.addProperty("status", "UNSUPPORTED_CONTAINER_NBT"); return row;
        }
        ListTag items = saved.getList("Items", Tag.TAG_COMPOUND);
        int inspected = Math.min(slots, MAX_SLOTS);
        int wheat = 0, total = 0;
        boolean[] seen = new boolean[inspected];
        for (int i = 0; i < items.size(); i++) {
            CompoundTag item = items.getCompound(i);
            if (!item.contains("Slot", Tag.TAG_BYTE) || !item.contains("Count", Tag.TAG_BYTE)
                    || !item.contains("id", Tag.TAG_STRING)) {
                row.addProperty("status", "MALFORMED_CONTAINER_NBT"); return row;
            }
            int slot = Byte.toUnsignedInt(item.getByte("Slot"));
            int count = item.getByte("Count");
            if (slot >= slots || count < 0) {
                row.addProperty("status", "MALFORMED_CONTAINER_NBT"); return row;
            }
            if (slot >= inspected) continue;
            if (seen[slot]) { row.addProperty("status", "MALFORMED_CONTAINER_NBT"); return row; }
            seen[slot] = true; total += count;
            if (item.getString("id").equals("minecraft:wheat")) wheat += count;
        }
        row.addProperty("status", slots <= MAX_SLOTS ? "OBSERVED" : "PARTIAL_SLOT_LIMIT");
        row.addProperty("slots", slots); row.addProperty("inspected_slots", inspected);
        row.addProperty("wheat", wheat); row.addProperty("total_items", total);
        row.addProperty("complete", slots <= MAX_SLOTS);
        return row;
    }

    private static Long typedLong(CompoundTag tag, String key) {
        return tag.contains(key, Tag.TAG_LONG) ? tag.getLong(key) : null;
    }
    private static BlockPos position(CompoundTag tag, String key) {
        return tag.contains(key, Tag.TAG_LONG) ? BlockPos.of(tag.getLong(key)) : null;
    }
    private static com.google.gson.JsonElement position(BlockPos position) {
        if (position == null) return JsonNull.INSTANCE;
        JsonArray values = new JsonArray();
        values.add(position.getX()); values.add(position.getY()); values.add(position.getZ());
        return values;
    }
    private static com.google.gson.JsonElement vector(Vec3 vector) {
        if (vector == null) return JsonNull.INSTANCE;
        JsonArray values = new JsonArray();
        for (double value : new double[] {vector.x, vector.y, vector.z})
            if (Double.isFinite(value)) values.add(value); else values.add(JsonNull.INSTANCE);
        return values;
    }
    private static com.google.gson.JsonElement node(Node node) {
        return node == null ? JsonNull.INSTANCE : position(new BlockPos(node.x, node.y, node.z));
    }
    private static String phaseName(Integer phase) {
        if (phase == null) return "ABSENT_OR_WRONG_TYPE";
        return switch (phase) {
            case 0 -> "TO_SOURCE"; case 1 -> "TO_DEST"; case 2 -> "COMPLETE";
            case 3 -> "PAUSED"; case 4 -> "QUARANTINED"; case 5 -> "INSERTING";
            case 6 -> "CANCELLED"; default -> "UNRECOGNIZED";
        };
    }
    private static String shortText(String text) {
        return text.length() <= MAX_TEXT ? text : text.substring(0, MAX_TEXT);
    }
    private static void value(JsonObject object, String key, Object value) {
        if (value == null || value instanceof Double number && !Double.isFinite(number))
            object.add(key, JsonNull.INSTANCE);
        else if (value instanceof Number number) object.addProperty(key, number);
        else if (value instanceof Boolean flag) object.addProperty(key, flag);
        else object.addProperty(key, value.toString());
    }
    private static int reply(CommandSourceStack source, JsonObject result) {
        String output = PREFIX + result;
        // RCON appends a line break to the component response.
        int bytes = output.getBytes(StandardCharsets.UTF_8).length + 1;
        if (bytes > MAX_REPLY_BYTES) {
            JsonObject bounded = new JsonObject();
            for (String key : new String[] {"schema", "world", "world_state", "dimension", "dimension_available", "tick",
                    "citizen", "loaded", "strictly_read_only", "atomic", "policy_control", "reward_authorized"})
                bounded.add(key, result.get(key));
            bounded.addProperty("status", "OVERSIZED_UNAVAILABLE");
            bounded.addProperty("snapshot_bytes", bytes);
            bounded.addProperty("max_reply_bytes", MAX_REPLY_BYTES);
            output = PREFIX + bounded;
        }
        final String message = output;
        source.sendSuccess(() -> Component.literal(message), false);
        return result.get("status").getAsString().equals("OBSERVED") && bytes <= MAX_REPLY_BYTES ? 1 : 0;
    }
}
