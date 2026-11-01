package dev.hearthbound.evidence;
import java.io.*;
import java.nio.*;
import java.nio.channels.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.CRC32;

/** Fsynced idempotent research credit journal; server-thread single writer. */
public final class DurableRewardLedger implements AutoCloseable {
 public record Reward(String citizenId,String domain,long milliPoints){
  public Reward {if(citizenId==null||citizenId.isBlank()||domain==null||domain.isBlank()||milliPoints<0)throw new IllegalArgumentException("bad reward");}
 }
 public record Credit(String eventId,List<Reward> rewards){
  public Credit {if(eventId==null||eventId.isBlank()||rewards==null||rewards.isEmpty())throw new IllegalArgumentException("bad credit");rewards=List.copyOf(rewards);}
 }
 private final FileChannel file;
 private final Map<String,Credit> known=new LinkedHashMap<>();
 private final Map<String,Long> totals=new HashMap<>();
 public DurableRewardLedger(Path path)throws IOException{
  Files.createDirectories(path.toAbsolutePath().getParent());
  file=FileChannel.open(path,StandardOpenOption.CREATE,StandardOpenOption.READ,StandardOpenOption.WRITE);
  try {recover();file.position(file.size());}catch(IOException|RuntimeException e){file.close();throw e;}
 }
 public synchronized boolean credit(Credit c)throws IOException{
  Objects.requireNonNull(c);if(known.containsKey(c.eventId()))return false;
  byte[] body=encode(c);if(body.length>65536)throw new IOException("oversize credit");
  Map<String,Long> changes=new HashMap<>();
  for(Reward r:c.rewards())changes.merge(key(r.citizenId(),r.domain()),r.milliPoints(),Math::addExact);
  for(var e:changes.entrySet())Math.addExact(totals.getOrDefault(e.getKey(),0L),e.getValue());
  CRC32 crc=new CRC32();crc.update(body);
  ByteBuffer frame=ByteBuffer.allocate(8+body.length).putInt(body.length).putInt((int)crc.getValue()).put(body);frame.flip();
  while(frame.hasRemaining())file.write(frame);file.force(true);apply(c);return true;
 }
 public synchronized boolean hasCredit(String id){return known.containsKey(id);}
 public synchronized long total(String citizen,String domain){return totals.getOrDefault(key(citizen,domain),0L);}
 public synchronized int creditCount(){return known.size();}
 private static String key(String citizen,String domain){return citizen+"\u0000"+domain;}
 private void apply(Credit c){known.put(c.eventId(),c);for(Reward r:c.rewards())totals.merge(key(r.citizenId(),r.domain()),r.milliPoints(),Math::addExact);}
 private void recover()throws IOException{
  file.position(0);
  while(file.position()<file.size()){
   long offset=file.position();ByteBuffer header=ByteBuffer.allocate(8);
   if(!read(header)){file.truncate(offset);break;}header.flip();int length=header.getInt(),expected=header.getInt();
   if(length<1||length>65536)throw new IOException("corrupt credit frame");
   ByteBuffer b=ByteBuffer.allocate(length);if(!read(b)){file.truncate(offset);break;}
   CRC32 crc=new CRC32();crc.update(b.array());if((int)crc.getValue()!=expected)throw new IOException("corrupt credit checksum");
   Credit c=decode(b.array());if(known.containsKey(c.eventId()))throw new IOException("duplicate credit record");
   try{apply(c);}catch(ArithmeticException e){throw new IOException("reward overflow",e);}
  }
 }
 private boolean read(ByteBuffer b)throws IOException{while(b.hasRemaining())if(file.read(b)<0)return false;return true;}
 private static byte[] encode(Credit c)throws IOException{
  ByteArrayOutputStream out=new ByteArrayOutputStream();
  try(DataOutputStream d=new DataOutputStream(out)){
   d.writeUTF(c.eventId());d.writeInt(c.rewards().size());
   for(Reward r:c.rewards()){d.writeUTF(r.citizenId());d.writeUTF(r.domain());d.writeLong(r.milliPoints());}
  }
  return out.toByteArray();
 }
 private static Credit decode(byte[] b)throws IOException{
  try(DataInputStream d=new DataInputStream(new ByteArrayInputStream(b))){
   String id=d.readUTF();int count=d.readInt();if(count<1||count>1024)throw new IOException("bad reward count");
   List<Reward> rewards=new ArrayList<>();for(int i=0;i<count;i++)rewards.add(new Reward(d.readUTF(),d.readUTF(),d.readLong()));
   if(d.available()!=0)throw new IOException("trailing credit bytes");return new Credit(id,rewards);
  }catch(IllegalArgumentException e){throw new IOException("bad credit",e);}
 }
 @Override public synchronized void close()throws IOException{file.close();}
}
