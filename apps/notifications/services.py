import re
from datetime import timedelta
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from .models import *
class TemplateRenderer:
    pattern=re.compile(r'{{\s*([\w.]+)\s*}}')
    @classmethod
    def render(cls,text,context):
        def repl(m):
            value=context
            for part in m.group(1).split('.'):
                value=value.get(part,'') if isinstance(value,dict) else getattr(value,part,'')
            return str(value if value is not None else '')
        return cls.pattern.sub(repl,text or '')
class NotificationService:
    @staticmethod
    def preference_enabled(org,user,event,channel):
        p=NotificationPreference.objects.filter(organization=org,user=user,event_code=event,channel=channel).first(); return p is None or p.enabled
    @staticmethod
    @transaction.atomic
    def create(org,user,event_code,title,message,link='',data=None,priority='normal',channels=None):
        n=Notification.objects.create(organization=org,recipient=user,event_code=event_code,title=title,message=message,link=link,data=data or {},priority=priority)
        channels=channels or [Channel.IN_APP]
        for ch in channels:
            if NotificationService.preference_enabled(org,user,event_code,ch): NotificationDelivery.objects.create(notification=n,channel=ch)
        NotificationAuditEvent.objects.create(organization=org,actor=user,event_code=event_code,action='created',notification=n,details={'channels':channels})
        return n
    @staticmethod
    def dispatch(org,event_code,context,actor=None):
        rules=NotificationRule.objects.filter(organization=org,event_code=event_code,is_active=True).select_related('template')
        total=0
        for rule in rules:
            if not NotificationService.matches(rule.condition,context): continue
            recipients=NotificationService.recipients(rule,org,actor)
            for user in recipients:
                title=TemplateRenderer.render(rule.template.subject_template if rule.template else context.get('title','Notification'),context)
                body=TemplateRenderer.render(rule.template.body_template if rule.template else context.get('message',''),context)
                NotificationService.create(org,user,event_code,title,body,context.get('link',''),context,rule.priority,rule.channels); total+=1
        return total
    @staticmethod
    def matches(condition,context): return all(str(context.get(k))==str(v) for k,v in condition.items())
    @staticmethod
    def recipients(rule,org,actor):
        if rule.recipient_strategy=='actor' and actor: return [actor]
        ids=rule.recipient_config.get('user_ids',[]) if isinstance(rule.recipient_config,dict) else []
        return list(org.members.filter(user_id__in=ids).select_related('user').values_list('user',flat=False)) if False else list(__import__('apps.accounts.models',fromlist=['User']).User.objects.filter(id__in=ids))
    @staticmethod
    def send_delivery(delivery):
        n=delivery.notification; delivery.attempt_count+=1
        try:
            if delivery.channel==Channel.EMAIL:
                email=getattr(n.recipient,'email','')
                if not email: raise ValueError('Recipient has no email')
                send_mail(n.title,n.message,None,[email],fail_silently=False)
            elif delivery.channel in (Channel.IN_APP,Channel.SMS,Channel.WEBHOOK): pass
            delivery.status=DeliveryStatus.SENT; delivery.sent_at=timezone.now(); delivery.error_message=''; delivery.save()
            return True
        except Exception as exc:
            delivery.status=DeliveryStatus.FAILED; delivery.error_message=str(exc); delivery.next_retry_at=timezone.now()+timedelta(minutes=min(60,2**delivery.attempt_count)); delivery.save(); return False
    @staticmethod
    def retry_failed(limit=100):
        qs=NotificationDelivery.objects.filter(status=DeliveryStatus.FAILED,next_retry_at__lte=timezone.now()).order_by('next_retry_at')[:limit]; return sum(NotificationService.send_delivery(d) for d in qs)
    @staticmethod
    def digest(org,user,start,end):
        ns=list(Notification.objects.filter(organization=org,recipient=user,created_at__gte=start,created_at__lt=end).order_by('created_at'))
        d=UserNotificationDigest.objects.create(organization=org,user=user,period_start=start,period_end=end,notification_ids=[str(n.pk) for n in ns],generated_at=timezone.now()); return d
class NotificationEventBus:
    EVENTS={'sales.order.created','sales.order.confirmed','finance.invoice.overdue','hr.leave.approved','payroll.payslip.generated','projects.task.assigned','support.ticket.created','support.ticket.sla_breached','documents.approval.requested','documents.approval.completed','ai.model.drift_detected'}
    @classmethod
    def publish(cls,org,event_code,context,actor=None): return NotificationService.dispatch(org,event_code,context,actor)
