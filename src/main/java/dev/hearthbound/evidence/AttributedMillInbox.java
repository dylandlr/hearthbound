package dev.hearthbound.evidence;
import java.io.*;
import java.nio.*;
import java.nio.channels.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.CRC32;

/** Durable attributed inbox. Single-writer server-thread ownership required. */
public final class AttributedMillInbox implements AutoCloseable {
 public record Entry(String eventId,String citizenId,String jobId,String dimension,String machine,long observedStartTick,long finishTick) {
  public Entry { if (bad(eventId)||bad(citizenId)||bad(jobId)||bad(dimension)||bad(machine)||observedStartTick<0||finishTick<=observedStartTick) throw new IllegalArgumentException("invalid receipt"); }
 }
 public interface Delivery { void deliver(Entry entry) throws Exception; }
 private final FileChannel file;
 private final Map<String,Entry> known=new LinkedHashMap<>();
 private final Set<String> acked=new HashSet<>();
 public AttributedMillInbox(Path path) throws IOException {
  Files.createDirectories(path.toAbsolutePath().getParent());
  file=FileChannel.open(path,StandardOpenOption.CREATE,StandardOpenOption.READ,StandardOpenOption.WRITE);
  try { recover(); file.position(file.size()); } catch(IOException|RuntimeException e) {file.close();throw e;}
 }
 public synchronized boolean enqueue(Entry e) throws IOException {
  Objects.requireNonNull(e);
  Entry old=known.get(e.eventId());
  if(old!=null) {if(!old.equals(e))throw new IOException("conflicting event attribution");return false;}
  append((byte)1,encode(e));known.put(e.eventId(),e);return true;
 }
 public synchronized void drain(Delivery d) throws Exception {
  for(Entry e:known.values())if(!acked.contains(e.eventId())) {d.deliver(e);append((byte)2,e.eventId().getBytes(java.nio.charset.StandardCharsets.UTF_8));acked.add(e.eventId());}
 }
 public synchronized int pendingCount(){return known.size()-acked.size();}
 public synchronized boolean isAcknowledged(String id){return acked.contains(id);}
 private void append(byte type,byte[] body)throws IOException{
  if(body.length>65535)throw new IOException("oversize frame");
  byte[] payload=new byte[body.length+1];payload[0]=type;System.arraycopy(body,0,payload,1,body.length);
  CRC32 crc=new CRC32();crc.update(payload);
  ByteBuffer frame=ByteBuffer.allocate(8+payload.length).putInt(payload.length).putInt((int)crc.getValue()).put(payload);frame.flip();
  while(frame.hasRemaining())file.write(frame);file.force(true);
 }
 private void recover()throws IOException{
  file.position(0);
  while(file.position()<file.size()){
   long offset=file.position();ByteBuffer h=ByteBuffer.allocate(8);
   if(!read(h)){file.truncate(offset);break;}h.flip();int len=h.getInt(),expected=h.getInt();
   if(len<2||len>65536)throw new IOException("corrupt inbox length");
   ByteBuffer b=ByteBuffer.allocate(len);if(!read(b)){file.truncate(offset);break;}
   byte[] payload=b.array();CRC32 crc=new CRC32();crc.update(payload);
   if((int)crc.getValue()!=expected)throw new IOException("corrupt inbox checksum");
   if(payload[0]==1){Entry e=decode(Arrays.copyOfRange(payload,1,payload.length));if(known.putIfAbsent(e.eventId(),e)!=null)throw new IOException("duplicate journal record");}
   else if(payload[0]==2){String id=new String(payload,1,payload.length-1,java.nio.charset.StandardCharsets.UTF_8);if(!known.containsKey(id)||!acked.add(id))throw new IOException("invalid ACK");}
   else throw new IOException("unknown frame");
  }
 }
 private boolean read(ByteBuffer b)throws IOException{while(b.hasRemaining())if(file.read(b)<0)return false;return true;}
 private static byte[] encode(Entry e)throws IOException{
  ByteArrayOutputStream out=new ByteArrayOutputStream();
  try(DataOutputStream d=new DataOutputStream(out)){d.writeUTF(e.eventId());d.writeUTF(e.citizenId());d.writeUTF(e.jobId());d.writeUTF(e.dimension());d.writeUTF(e.machine());d.writeLong(e.observedStartTick());d.writeLong(e.finishTick());}
  return out.toByteArray();
 }
 private static Entry decode(byte[] b)throws IOException{
  try(DataInputStream d=new DataInputStream(new ByteArrayInputStream(b))){
   Entry e=new Entry(d.readUTF(),d.readUTF(),d.readUTF(),d.readUTF(),d.readUTF(),d.readLong(),d.readLong());if(d.available()!=0)throw new IOException("trailing bytes");return e;
  }catch(IllegalArgumentException e){throw new IOException("invalid receipt",e);}
 }
 private static boolean bad(String s){return s==null||s.isBlank();}
 @Override public synchronized void close()throws IOException{file.close();}
}
