package dev.hearthbound.evidence;
import java.nio.file.*;
import java.util.*;
public final class JournalWorldBindingTest {
 static int checks;
 static void ok(boolean b){checks++;if(!b)throw new AssertionError("check "+checks);}
 static void fails(Thrower f)throws Exception{boolean bad=false;try{f.run();}catch(java.io.IOException e){bad=true;}ok(bad);}
 interface Thrower{void run()throws Exception;}
 public static void main(String[] args)throws Exception{
  Path dir=Files.createTempDirectory("hb-journal-world"),inbox=dir.resolve("inbox.bin"),reward=dir.resolve("rewards.bin");
  UUID one=UUID.randomUUID(),two=UUID.randomUUID();
  try{
   ok(JournalWorldBinding.verify(dir,one,inbox,reward)==JournalWorldBinding.Result.RESTART_REQUIRED);
   ok(JournalWorldBinding.verify(dir,one,inbox,reward)==JournalWorldBinding.Result.VERIFIED);
   Files.write(inbox,new byte[0]);
   ok(JournalWorldBinding.verify(dir,one,inbox,reward)==JournalWorldBinding.Result.VERIFIED);
   fails(()->JournalWorldBinding.verify(dir,two,inbox,reward));
   Path marker=dir.resolve("hearthbound-journals.world");
   Files.delete(marker);
   fails(()->JournalWorldBinding.verify(dir,one,inbox,reward));
   Files.delete(inbox);
   Files.writeString(marker,"corrupted");
   fails(()->JournalWorldBinding.verify(dir,one,inbox,reward));
   Files.delete(marker);
   fails(()->JournalWorldBinding.verify(dir,one,dir.resolve("elsewhere").resolve("inbox"),reward));
   ok(JournalWorldBinding.verify(dir,one,inbox,reward)==JournalWorldBinding.Result.RESTART_REQUIRED);
   ok(JournalWorldBinding.verify(dir,one,inbox,reward)==JournalWorldBinding.Result.VERIFIED);
   System.out.println("PASS "+checks+" checks");
  }finally{try(var files=Files.walk(dir)){files.sorted(Comparator.reverseOrder()).forEach(p->{try{Files.deleteIfExists(p);}catch(Exception e){throw new RuntimeException(e);}});}}
 }
}
