import hashlib, json, uuid
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import *

class Correlation:
    @staticmethod
    def new(prefix="EO"): return f"{prefix}-{uuid.uuid4().hex}"

class EventBus:
    """Durable outbox-style event publisher with idempotency."""
    @staticmethod
    @transaction.atomic
    def emit(organization, event_code, aggregate_type, aggregate_id, payload, *, correlation_id=None, idempotency_key=None):
        key=idempotency_key or hashlib.sha256(json.dumps([event_code,aggregate_type,str(aggregate_id),payload],sort_keys=True,default=str).encode()).hexdigest()
        event,created=IntegrationEvent.objects.get_or_create(idempotency_key=key,defaults={
            "organization":organization,"event_code":event_code,"aggregate_type":aggregate_type,"aggregate_id":str(aggregate_id),"payload":payload,"correlation_id":correlation_id or Correlation.new(),
        })
        return event,created

class MappingEngine:
    @staticmethod
    def transform(record, mapping):
        output=dict(mapping.defaults or {})
        for target,source in (mapping.field_map or {}).items():
            if isinstance(source,str): value=record.get(source)
            else: value=source
            rule=(mapping.transforms or {}).get(target)
            if rule == "string" and value is not None: value=str(value)
            elif rule == "lower" and value is not None: value=str(value).lower()
            elif rule == "upper" and value is not None: value=str(value).upper()
            elif rule == "int" and value is not None: value=int(value)
            elif rule == "float" and value is not None: value=float(value)
            output[target]=value
        return output

class IdempotencyService:
    @staticmethod
    def key(namespace, payload):
        raw=json.dumps([namespace,payload],sort_keys=True,default=str).encode(); return hashlib.sha256(raw).hexdigest()
    @staticmethod
    def already_processed(model, key): return model.objects.filter(idempotency_key=key).exists()

class IntegrationRunner:
    @staticmethod
    @transaction.atomic
    def start(job, *, correlation_id=None):
        run=IntegrationJobRun.objects.create(job=job,status=RunStatus.RUNNING,correlation_id=correlation_id or Correlation.new("JOB"),started_at=timezone.now())
        return run
    @staticmethod
    def finish(run, processed, succeeded, failed, error=""):
        run.processed_count=processed; run.success_count=succeeded; run.failed_count=failed; run.error_message=error
        run.duration_ms=max(0,int((timezone.now()-(run.started_at or timezone.now())).total_seconds()*1000))
        run.status=RunStatus.SUCCEEDED if failed==0 else (RunStatus.PARTIAL if succeeded else RunStatus.FAILED); run.finished_at=timezone.now(); run.save()
        return run

class RetryPolicy:
    @staticmethod
    def next_attempt(attempt, base_seconds=30, maximum_minutes=60):
        seconds=min(base_seconds*(2**max(attempt-1,0)),maximum_minutes*60)
        return timezone.now()+timedelta(seconds=seconds)

class ReconciliationEngine:
    @staticmethod
    def compare(run, source, target, key="id"):
        source_map={str(x.get(key)):x for x in source}; target_map={str(x.get(key)):x for x in target}
        matched=mismatched=0
        for external_key in sorted(set(source_map)|set(target_map)):
            s,t=source_map.get(external_key),target_map.get(external_key)
            if s is None or t is None:
                status="MISSING_SOURCE" if s is None else "MISSING_TARGET"; differences=[status]
            elif s==t: status="MATCHED"; differences=[]
            else:
                status="MISMATCHED"; differences=[k for k in set(s)|set(t) if s.get(k)!=t.get(k)]
            ReconciliationItem.objects.create(run=run,external_key=external_key,status=status,source_value=s or {},target_value=t or {},differences=differences)
            matched += status=="MATCHED"; mismatched += status!="MATCHED"
        run.source_count=len(source); run.target_count=len(target); run.matched_count=matched; run.mismatch_count=mismatched
        run.status=RunStatus.SUCCEEDED; run.started_at=run.started_at or timezone.now(); run.finished_at=timezone.now(); run.summary={"match_rate": round(matched/max(len(set(source_map)|set(target_map)),1)*100,2)}; run.save(); return run

class ReleaseGate:
    REQUIRED=("syntax","configuration","migrations","security","tests","documentation","static_assets")
    @classmethod
    def evaluate(cls, release):
        checks=list(release.checks.all()); required=[c for c in checks if c.required]
        passed=bool(required) and all(c.passed for c in required)
        release.status="READY" if passed else "BLOCKED"; release.save(update_fields=["status"]); return passed

class ConfigurationResolver:
    @staticmethod
    def get(organization,key,environment="production",default=None):
        row=SystemConfiguration.objects.filter(organization=organization,key=key,environment=environment).first()
        return row.value if row else default
    @staticmethod
    def set(organization,key,value,*,environment="production",updated_by=None,encrypted=False,description=""):
        row,created=SystemConfiguration.objects.get_or_create(organization=organization,key=key,environment=environment,defaults={"value":value,"updated_by":updated_by,"encrypted":encrypted,"description":description})
        if not created:
            row.value=value; row.version+=1; row.updated_by=updated_by; row.encrypted=encrypted; row.description=description; row.save()
        return row

class FeatureFlagService:
    @staticmethod
    def enabled(key, organization=None, environment="production", context=None):
        row=FeatureFlag.objects.filter(key=key,organization=organization).first() or FeatureFlag.objects.filter(key=key,organization__isnull=True).first()
        if not row or not row.enabled or (row.environments and environment not in row.environments): return False
        if row.rollout_percent>=100: return True
        seed=json.dumps([key,(context or {}).get("user_id","")]).encode(); bucket=int(hashlib.sha256(seed).hexdigest()[:8],16)%100
        return bucket < row.rollout_percent

class HealthReadiness:
    @staticmethod
    def summary():
        checks={}
        for label,fn in [("database",lambda: __import__("django.db").db.connection.ensure_connection()),("models",lambda: IntegrationConnection.objects.count())]:
            try: fn(); checks[label]={"status":"ok"}
            except Exception as exc: checks[label]={"status":"error","message":str(exc)}
        ready=all(x["status"]=="ok" for x in checks.values())
        return {"status":"ready" if ready else "degraded","checks":checks,"timestamp":timezone.now().isoformat()}

class FinalizationReport:
    @staticmethod
    def build():
        return {"connections":IntegrationConnection.objects.count(),"jobs":IntegrationJob.objects.count(),"events":IntegrationEvent.objects.count(),"dead_letters":DeadLetterEvent.objects.filter(resolved=False).count(),"reconciliations":ReconciliationRun.objects.count(),"releases":ReleaseRecord.objects.count()}
