from datetime import timedelta
from django.utils import timezone
from .models import Document, DocumentCategory, DocumentRetentionPolicy, DocumentRetentionEvent, DocumentStatus
class RetentionPolicyEngine:
    @staticmethod
    def resolve(document):
        policy=DocumentRetentionPolicy.objects.filter(organization=document.organization,is_active=True,category=document.category).order_by("-retention_days").first()
        if not policy: policy=DocumentRetentionPolicy.objects.filter(organization=document.organization,is_active=True,category__isnull=True).order_by("-retention_days").first()
        return policy
    @staticmethod
    def schedule(document):
        policy=RetentionPolicyEngine.resolve(document)
        if not policy: return []
        base=document.created_at or timezone.now(); events=[]
        for event_type,days in [("expire",policy.retention_days),("archive",policy.archive_after_days)]:
            if days<=0: continue
            when=base+timedelta(days=days); e,created=DocumentRetentionEvent.objects.get_or_create(document=document,policy=policy,event_type=event_type,defaults={"scheduled_for":when})
            events.append(e)
        return events
    @staticmethod
    def legal_hold(document,enabled=True):
        meta=dict(document.metadata or {}); meta["legal_hold"]=bool(enabled); meta["legal_hold_at"]=timezone.now().isoformat() if enabled else None; document.metadata=meta; document.save(update_fields=["metadata","updated_at"]); return document
    @staticmethod
    def is_on_hold(document): return bool((document.metadata or {}).get("legal_hold"))
    @staticmethod
    def expire_candidates(org):
        now=timezone.now(); return Document.objects.filter(organization=org,expires_at__lte=now).exclude(status__in=[DocumentStatus.ARCHIVED,DocumentStatus.EXPIRED])
class DocumentLifecycle: 
    @staticmethod
    def archive_if_eligible(document,user=None):
        if RetentionPolicyEngine.is_on_hold(document): return False
        if document.status!=DocumentStatus.ARCHIVED: document.status=DocumentStatus.ARCHIVED; document.archived_at=timezone.now(); document.save(update_fields=["status","archived_at","updated_at"]); return True
        return False
