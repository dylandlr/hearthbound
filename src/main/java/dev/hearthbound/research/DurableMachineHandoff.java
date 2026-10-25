package dev.hearthbound.research;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import static java.nio.file.StandardOpenOption.*;

/**
 * Crash-durable handoff journal, separate from legacy unresolved fixture claims.
 * A new owner may acquire only after the prior owner has been durably retired.
 * All operations on a machine serialize through one filesystem lock.
 */
public final class DurableMachineHandoff {
    private static final int VERSION=1;
    private final Path dir;
    public record Owner(UUID operation, UUID citizen, long generation) {}
    public record State(Owner owner, boolean retired) {}
    public DurableMachineHandoff(Path existingDirectory) { dir=Objects.requireNonNull(existingDirectory).toAbsolutePath(); }

    private Path path(String machine) {
        if(machine==null||machine.isBlank()) throw new IllegalArgumentException("Missing machine key");
        try {
            byte[] hash=MessageDigest.getInstance("SHA-256").digest(machine.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            return dir.resolve(HexFormat.of().formatHex(hash)+".handoff");
        } catch(java.security.NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }
    private State read(Path target) throws IOException {
        if(!Files.exists(target)) return null;
        byte[] data=Files.readAllBytes(target);
        if(data.length!=4+16+16+8+1+32) throw new IOException("Corrupt handoff state length");
        byte[] body=Arrays.copyOf(data,data.length-32);
        try {
            byte[] digest=MessageDigest.getInstance("SHA-256").digest(body);
            if(!MessageDigest.isEqual(digest,Arrays.copyOfRange(data,body.length,data.length)))
                throw new IOException("Corrupt handoff digest");
        } catch(java.security.NoSuchAlgorithmException impossible) {throw new AssertionError(impossible);}
        ByteBuffer b=ByteBuffer.wrap(body);
        if(b.getInt()!=VERSION) throw new IOException("Wrong handoff version");
        UUID operation=new UUID(b.getLong(),b.getLong());
        UUID citizen=new UUID(b.getLong(),b.getLong());
        long generation=b.getLong();
        byte retired=b.get();
        if(generation<1||(retired!=0&&retired!=1)) throw new IOException("Invalid handoff");
        return new State(new Owner(operation,citizen,generation),retired==1);
    }
    private void write(Path target,State state) throws IOException {
        ByteBuffer b=ByteBuffer.allocate(45);
        b.putInt(VERSION).putLong(state.owner.operation.getMostSignificantBits())
         .putLong(state.owner.operation.getLeastSignificantBits())
         .putLong(state.owner.citizen.getMostSignificantBits())
         .putLong(state.owner.citizen.getLeastSignificantBits())
         .putLong(state.owner.generation).put((byte)(state.retired?1:0));
        byte[] body=b.array();
        byte[] digest;
        try {digest=MessageDigest.getInstance("SHA-256").digest(body);}
        catch(java.security.NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}
        Path tmp=Files.createTempFile(dir,"handoff-",".pending");
        try {
            try(FileChannel out=FileChannel.open(tmp,WRITE)) {
                out.write(ByteBuffer.wrap(body));out.write(ByteBuffer.wrap(digest));out.force(true);
            }
            Files.move(tmp,target,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
            try(FileChannel directory=FileChannel.open(dir,READ)){directory.force(true);}
        } finally {Files.deleteIfExists(tmp);}
    }
    private interface Transition<T>{T apply(Path path, State existing) throws IOException;}
    private synchronized <T> T locked(String machine,Transition<T> change) throws IOException {
        Path target=path(machine);
        try(FileChannel lock=FileChannel.open(dir.resolve("handoff.lock"),CREATE,WRITE);
            var held=lock.lock()) {
            return change.apply(target,read(target));
        }
    }
    public State current(String machine) throws IOException {return locked(machine,(p,s)->s);}
    public State acquire(String machine,UUID operation,UUID citizen) throws IOException {
        Objects.requireNonNull(operation);Objects.requireNonNull(citizen);
        return locked(machine,(p,s)->{
            if(s!=null&&!s.retired) {
                if(s.owner.operation.equals(operation)&&s.owner.citizen.equals(citizen))return s;
                throw new IOException("Machine occupied by another operation");
            }
            // Retired operations must not be revived with their old ID.
            if(s!=null&&s.owner.operation.equals(operation)) throw new IOException("Retired operation cannot reactivate");
            State next=new State(new Owner(operation,citizen,s==null?1:Math.addExact(s.owner.generation,1)),false);
            write(p,next);return next;
        });
    }
    /** verified proof is an eligibility decision from the trusted receipt gate, not a client flag. */
    public State retire(String machine,UUID operation,UUID citizen, MachineClaimRetirementGate.Decision decision)
            throws IOException {
        if(decision!=MachineClaimRetirementGate.Decision.ELIGIBLE_FOR_RETIREMENT)
            throw new IOException("Retirement evidence not accepted");
        return locked(machine,(p,s)->{
            if(s==null||!s.owner.operation.equals(operation)||!s.owner.citizen.equals(citizen))
                throw new IOException("Machine owner mismatch");
            if(s.retired)return s;
            State next=new State(s.owner,true);write(p,next);return next;
        });
    }
}
