"""Pure experimental timeline; never mutates world or exposes actor state."""
from dataclasses import dataclass, asdict
import hashlib
import json
import math

TYPES = frozenset({'crop_failure','mill_failure','specialist_loss','resource_depletion','communication_failure','demand_change'})

@dataclass(frozen=True)
class Event:
    event_id: str
    kind: str
    onset: int
    duration: int
    severity: float
    def __post_init__(self):
        if not isinstance(self.event_id,str) or not self.event_id.strip() or self.kind not in TYPES:
            raise ValueError('invalid identity or type')
        if type(self.onset) is not int or type(self.duration) is not int or self.onset < 0 or self.duration <= 0:
            raise ValueError('invalid interval')
        if type(self.severity) not in (int,float) or not 0 <= self.severity <= 1 or not math.isfinite(self.severity):
            raise ValueError('invalid severity')

class Scheduler:
    def __init__(self, events):
        events = tuple(events)
        if any(not isinstance(e,Event) for e in events) or len({e.event_id for e in events}) != len(events):
            raise ValueError('invalid or duplicate events')
        self.events = tuple(sorted(events,key=lambda e:e.event_id))
        self.digest = hashlib.sha256(json.dumps([asdict(e) for e in self.events],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.cursor = -1
        self.timeline = sorted((tick,phase,e.event_id) for e in self.events for tick,phase in ((e.onset,1),(e.onset+e.duration,0)))
    def advance(self,tick):
        if type(tick) is not int or tick < 0 or tick < self.cursor:
            raise ValueError('invalid clock')
        transitions = [(t,'start' if p else 'end',i) for t,p,i in self.timeline if self.cursor < t <= tick]
        self.cursor = tick
        return transitions
    def snapshot(self):
        return {'version':1,'schedule_sha256':self.digest,'cursor':self.cursor}
    @classmethod
    def restore(cls,events,state):
        obj=cls(events)
        if not isinstance(state,dict) or set(state)!= {'version','schedule_sha256','cursor'} or type(state['version']) is not int or state['version']!=1 or state['schedule_sha256']!=obj.digest or type(state['cursor']) is not int or state['cursor'] < -1:
            raise ValueError('invalid snapshot')
        obj.cursor=state['cursor']
        return obj
