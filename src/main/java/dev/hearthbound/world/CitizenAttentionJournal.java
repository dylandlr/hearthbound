package dev.hearthbound.world;

import com.google.gson.JsonObject;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;

/**
 * Explicitly enabled experiment journal. One append per completed decision/outcome
 * pair, with a run-specific file and tamper-evident hash chain. No AI action
 * execution or global source queries. File writes occur on the Forge tick thread;
 * keep disabled outside small controlled research experiments.
 */
public final class CitizenAttentionJournal {
    public static final String SCHEMA="hearthbound.attention-journal.v1";
    public static final long MAX_RECORDS=50000L;
    private static final Map<ServerLevel, Session> SESSIONS=new WeakHashMap<>();

    private static final class Session {
        final String runId;
        final Path file;
        long sequence;
        String previousHash="GENESIS";
        boolean active=true;
        String lastError="NONE";
        Session(String runId,Path file) { this.runId=runId; this.file=file; }
    }
    private CitizenAttentionJournal() {}

    public static String start(ServerLevel level) {
        if(level==null) throw new IllegalArgumentException("missing level");
        Session old=SESSIONS.get(level);
        if(old!=null && old.active)
            return "ATTENTION_JOURNAL status=ALREADY_ACTIVE run_id="+old.runId+" action_authorized=false";
        String id=UUID.randomUUID().toString();
        Path root=level.getServer().getWorldPath(LevelResource.ROOT)
            .resolve("hearthbound-attention");
        Path file=root.resolve("attention-"+id+".jsonl");
        try {
            Files.createDirectories(root);
            Files.createFile(file); // refuse overwrite, even on UUID collision
            Session session=new Session(id,file);
            SESSIONS.put(level,session);
            return "ATTENTION_JOURNAL status=STARTED run_id="+session.runId
                +" max_records="+MAX_RECORDS+" action_authorized=false";
        } catch(IOException error) {
            return "ATTENTION_JOURNAL status=ABSTAIN reason=IO_FAILURE action_authorized=false";
        }
    }

    public static String stop(ServerLevel level) {
        if(level==null) throw new IllegalArgumentException("missing level");
        Session session=SESSIONS.get(level);
        if(session==null)
            return "ATTENTION_JOURNAL status=INACTIVE action_authorized=false";
        session.active=false;
        return "ATTENTION_JOURNAL status=STOPPED run_id="+session.runId
            +" records="+session.sequence+" action_authorized=false";
    }

    public static String status(ServerLevel level) {
        if(level==null) throw new IllegalArgumentException("missing level");
        Session session=SESSIONS.get(level);
        if(session==null)
            return "ATTENTION_JOURNAL status=INACTIVE action_authorized=false";
        return "ATTENTION_JOURNAL status="+(session.active?"ACTIVE":"STOPPED")
            +" run_id="+session.runId+" records="+session.sequence
            +" last_error="+session.lastError+" action_authorized=false";
    }

    private static String hash(String raw) {
        try {
            byte[] digest=MessageDigest.getInstance("SHA-256")
                .digest(raw.getBytes(StandardCharsets.UTF_8));
            StringBuilder value=new StringBuilder();
            for(byte piece:digest) value.append(String.format("%02x",piece&255));
            return value.toString();
        } catch(NoSuchAlgorithmException unavailable) {
            throw new IllegalStateException("SHA-256 unavailable",unavailable);
        }
    }

    /** Called only when a recorded opportunity has a matching completed outcome. */
    public static void append(ServerLevel level,String choice,String outcome) {
        Session session=SESSIONS.get(level);
        if(session==null || !session.active) return;
        if(session.sequence>=MAX_RECORDS) {
            session.active=false;
            session.lastError="RECORD_CAP";
            return;
        }
        String payload=Base64.getUrlEncoder().withoutPadding().encodeToString(
            (choice+"\n"+outcome).getBytes(StandardCharsets.UTF_8));
        String digest=hash(session.previousHash+"\n"+payload);
        JsonObject entry=new JsonObject();
        entry.addProperty("schema",SCHEMA);
        entry.addProperty("run_id",session.runId);
        entry.addProperty("sequence",session.sequence+1);
        entry.addProperty("previous_hash",session.previousHash);
        entry.addProperty("payload_b64",payload);
        entry.addProperty("sha256",digest);
        try {
            Files.writeString(session.file,entry.toString()+"\n",
                StandardCharsets.UTF_8,StandardOpenOption.APPEND);
            session.sequence++;
            session.previousHash=digest;
        } catch(IOException error) {
            // Fail closed for evidence capture; do not pretend success.
            session.active=false;
            session.lastError="IO_FAILURE";
        }
    }
}
