import unittest
from event_scheduler import Event, Scheduler

class SchedulerTests(unittest.TestCase):
    def event(self,id='a',onset=2,duration=3):
        return Event(id,'crop_failure',onset,duration,.4)
    def test_empty(self):
        self.assertEqual(Scheduler([]).advance(100),[])
    def test_boundary(self):
        s=Scheduler([self.event()]); self.assertEqual(s.advance(1),[]); self.assertEqual(s.advance(2),[(2,'start','a')]); self.assertEqual(s.advance(5),[(5,'end','a')])
    def test_skipped_overlap(self):
        s=Scheduler([self.event('b',5),self.event('a'),self.event('c',3)])
        self.assertEqual(s.advance(10),[(2,'start','a'),(3,'start','c'),(5,'end','a'),(5,'start','b'),(6,'end','c'),(8,'end','b')])
    def test_order(self):
        a,b=self.event('a'),self.event('b'); self.assertEqual(Scheduler([a,b]).advance(9),Scheduler([b,a]).advance(9))
    def test_restart(self):
        e=[self.event()]; s=Scheduler(e); s.advance(2); r=Scheduler.restore(e,s.snapshot()); self.assertEqual(r.advance(2),[]); self.assertEqual(r.advance(5),[(5,'end','a')])
    def test_duplicate(self):
        with self.assertRaises(ValueError): Scheduler([self.event(),self.event()])
    def test_invalid(self):
        for args in [('a','unknown',0,1,.5),('a','crop_failure',True,1,.5),('a','crop_failure',0,0,.5),('a','crop_failure',0,1,float('nan')),('a','crop_failure',0,1,2)]:
            with self.subTest(args=args),self.assertRaises(ValueError): Event(*args)
    def test_clock(self):
        s=Scheduler([]); s.advance(3)
        with self.assertRaises(ValueError): s.advance(2)
    def test_snapshot(self):
        e=[self.event()]; s=Scheduler(e)
        for state in [{},dict(s.snapshot(),cursor=True),dict(s.snapshot(),schedule_sha256='bad')]:
            with self.assertRaises(ValueError): Scheduler.restore(e,state)
if __name__=='__main__': unittest.main()
