from dataclasses import dataclass,field
from .services import NotificationEventBus,NotificationService
@dataclass
class DomainEvent:
    organization: object
    code: str
    actor: object=None
    context: dict=field(default_factory=dict)
class EventDispatcher:
    def __init__(self): self.published=[]
    def publish(self,event):
        count=NotificationEventBus.publish(event.organization,event.code,event.context,event.actor); self.published.append((event.code,count)); return count
    def publish_many(self,events): return sum(self.publish(e) for e in events)
def publish(organization,code,actor=None,**context): return NotificationEventBus.publish(organization,code,context,actor)
