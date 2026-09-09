"""Security domain services: policy enforcement, auditing, risk and incidents."""
import hashlib, json, secrets
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import *

class AuditService:
    SENSITIVE={"password","password_hash","token","secret","challenge_hash","code_hash"}
    @staticmethod
    def sanitize(data):
        if not isinstance(data,dict): return data
        return {k:("[REDACTED]" if k.lower() in AuditService.SENSITIVE else v) for k,v in data.items()}
    @staticmethod
    def diff(before,after):
        before=AuditService.sanitize(before or {}); after=AuditService.sanitize(after or {})
        keys=sorted(set(before)|set(after)); changed=[k for k in keys if before.get(k)!=after.get(k)]
        return changed,before,after
    @classmethod
    def record(cls, *, actor=None, organization=None, action="READ", instance=None, before=None, after=None, request=None, reason=""):
        changed,before,after=cls.diff(before,after)
        return AuditEntry.objects.create(actor=actor,organization=organization,action=action,model_label=instance._meta.label if instance else "unknown",object_id=str(instance.pk) if instance else "",object_repr=str(instance)[:500] if instance else "",before_data=before,after_data=after,changed_fields=changed,ip_address=getattr(request,"client_ip",None),user_agent=getattr(request,"client_user_agent",""),request_id=getattr(request,"request_id",""),reason=reason)
    @classmethod
    def login(cls,user,success,request=None,reason=""):
        return cls.record(actor=user,action="LOGIN",instance=user,after={"success":success},request=request,reason=reason)

class SecurityEventService:
    @classmethod
    def emit(cls,event_type,*,user=None,organization=None,severity="INFO",outcome="SUCCESS",request=None,action="",resource=None,metadata=None,risk_score=0):
        return SecurityEvent.objects.create(event_type=event_type,user=user,organization=organization,severity=severity,outcome=outcome,ip_address=getattr(request,"client_ip",None),user_agent=getattr(request,"client_user_agent",""),request_id=getattr(request,"request_id",""),action=action,resource_type=resource._meta.label if resource else "",resource_id=str(resource.pk) if resource else "",metadata=metadata or {},risk_score=risk_score)
    @classmethod
    def calculate_risk(cls,event):
        score=0
        score += {"INFO":0,"LOW":10,"MEDIUM":30,"HIGH":60,"CRITICAL":90}.get(event.severity,0)
        if event.outcome in {"FAILURE","BLOCKED"}: score+=15
        if event.ip_address and event.ip_address.startswith(("10.","192.168.")): score=max(0,score-5)
        return min(score,100)

class PolicyEngine:
    @staticmethod
    def active_policy(organization): return SecurityPolicy.objects.filter(organization=organization,is_active=True).order_by("-updated_at").first()
    @classmethod
    def password_rules(cls,organization):
        p=cls.active_policy(organization)
        return {"min_length":p.password_min_length if p else 10,"history":p.password_history_count if p else 5}
    @classmethod
    def _ip_matches(cls, ip, entry):
        if ip == entry: return True
        try:
            import ipaddress
            if "/" in entry:
                return ipaddress.ip_address(ip) in ipaddress.ip_network(entry, strict=False)
        except Exception:
            pass
        return False
    @classmethod
    def ip_allowed(cls,organization,ip):
        p=cls.active_policy(organization)
        if not p: return True
        for b in (p.ip_blocklist or []):
            if cls._ip_matches(ip, b): return False
        allow=p.ip_allowlist or []
        if not allow: return True
        for a in allow:
            if cls._ip_matches(ip, a): return True
        return False
    @classmethod
    def create_version(cls,policy,actor=None,reason=""):
        last=policy.versions.order_by("-version").first(); version=(last.version if last else 0)+1
        snapshot={f.name:getattr(policy,f.name) for f in policy._meta.fields if f.name not in {"id","created_at","updated_at","created_by"}}
        return SecurityPolicyVersion.objects.create(policy=policy,version=version,snapshot=snapshot,created_by=actor,change_reason=reason)

class SessionSecurityService:
    @classmethod
    def register(cls,user,session_key,request=None,device_fingerprint="",device_name=""):
        return UserSession.objects.update_or_create(session_key=session_key,defaults={"user":user,"ip_address":getattr(request,"client_ip",None),"user_agent":getattr(request,"client_user_agent",""),"device_fingerprint":device_fingerprint,"device_name":device_name,"status":"ACTIVE","last_seen_at":timezone.now()})
    @classmethod
    def touch(cls,session_key):
        return UserSession.objects.filter(session_key=session_key,status="ACTIVE").update(last_seen_at=timezone.now())
    @classmethod
    def revoke(cls,session_key,reason="Administrative revocation"):
        return UserSession.objects.filter(session_key=session_key).update(status="REVOKED",revoked_at=timezone.now(),revoke_reason=reason)
    @classmethod
    def revoke_all(cls,user,except_session=None,reason="Global logout"):
        qs=UserSession.objects.filter(user=user,status="ACTIVE")
        if except_session: qs=qs.exclude(session_key=except_session)
        return qs.update(status="REVOKED",revoked_at=timezone.now(),revoke_reason=reason)
    @classmethod
    def expire_stale(cls,minutes=480):
        cutoff=timezone.now()-timedelta(minutes=minutes)
        return UserSession.objects.filter(status="ACTIVE",last_seen_at__lt=cutoff).update(status="EXPIRED",revoked_at=timezone.now(),revoke_reason="Session timeout")

class MFAService:
    @staticmethod
    def hash_code(code): return hashlib.sha256(code.encode()).hexdigest()
    @classmethod
    def issue(cls,user,method="EMAIL",ttl_minutes=10):
        code=f"{secrets.randbelow(1000000):06d}"
        challenge=MFAChallenge.objects.create(user=user,method=method,challenge_hash=cls.hash_code(code),expires_at=timezone.now()+timedelta(minutes=ttl_minutes))
        return challenge,code
    @classmethod
    def verify(cls,challenge,code):
        if challenge.status!="PENDING" or challenge.expires_at<=timezone.now():
            challenge.status="EXPIRED"; challenge.save(update_fields=["status"]); return False
        if challenge.attempts>=challenge.max_attempts:
            challenge.status="FAILED"; challenge.save(update_fields=["status"]); return False
        challenge.attempts+=1
        if secrets.compare_digest(challenge.challenge_hash,cls.hash_code(code)):
            challenge.status="VERIFIED"; challenge.verified_at=timezone.now(); challenge.save(update_fields=["attempts","status","verified_at"]); return True
        if challenge.attempts>=challenge.max_attempts: challenge.status="FAILED"
        challenge.save(update_fields=["attempts","status"]); return False
    @classmethod
    def recovery_codes(cls,user,count=10):
        created=[]
        for _ in range(count):
            raw=secrets.token_urlsafe(8).upper(); obj=MFARecoveryCode.objects.create(user=user,code_hash=cls.hash_code(raw)); created.append(raw)
        return created

class AccessReviewService:
    @classmethod
    @transaction.atomic
    def create(cls,organization,reviewer,title,users,permissions):
        review=AccessReview.objects.create(organization=organization,reviewer=reviewer,title=title,status="OPEN")
        for user in users:
            for perm in permissions:
                AccessReviewItem.objects.create(review=review,user=user,permission_code=perm,current_value={"granted":user.has_enterprise_perm(perm)})
        return review
    @classmethod
    def decide(cls,item,decision,reviewer_comment=""):
        item.decision=decision; item.reviewer_comment=reviewer_comment; item.decided_at=timezone.now(); item.save(update_fields=["decision","reviewer_comment","decided_at"]); return item
    @classmethod
    def complete(cls,review,notes=""):
        review.status="COMPLETED"; review.completed_at=timezone.now(); review.notes=notes; review.save(update_fields=["status","completed_at","notes"]); return review
    @classmethod
    def completion_ratio(cls,review):
        total=review.items.count(); decided=review.items.exclude(decision="PENDING").count(); return 1 if not total else round(decided/total,4)

class IncidentService:
    @classmethod
    def create(cls,organization,title,description,category,priority="P3",source_event=None):
        return SecurityIncident.objects.create(organization=organization,title=title,description=description,category=category,priority=priority,source_event=source_event)
    @classmethod
    def add_event(cls,incident,event_type,message,actor=None,metadata=None): return IncidentEvent.objects.create(incident=incident,event_type=event_type,message=message,actor=actor,metadata=metadata or {})
    @classmethod
    def transition(cls,incident,status,actor=None,message=""):
        old=incident.status; incident.status=status
        if status in {"RESOLVED","CLOSED"}: incident.resolved_at=timezone.now()
        incident.save(update_fields=["status","resolved_at"] if status in {"RESOLVED","CLOSED"} else ["status"])
        cls.add_event(incident,"STATUS_CHANGE",message or f"{old} -> {status}",actor,{"from":old,"to":status}); return incident
    @classmethod
    def detect_from_event(cls,event):
        if event.severity not in {"HIGH","CRITICAL"}: return None
        title=f"{event.severity} security event: {event.event_type}"
        incident=cls.create(event.organization,title,f"Automatically created from security event {event.id}",event.event_type,"P1" if event.severity=="CRITICAL" else "P2",event)
        cls.add_event(incident,"AUTO_DETECTED","Incident created by event detection engine",event.user,{"event_id":str(event.id)})
        return incident

class AlertEngine:
    @classmethod
    def evaluate(cls,event):
        if not event.organization: return []
        rules=SecurityAlertRule.objects.filter(organization=event.organization,is_active=True,event_type=event.event_type)
        created=[]
        for rule in rules:
            qs=SecurityEvent.objects.filter(organization=event.organization,event_type=event.event_type,occurred_at__gte=timezone.now()-timedelta(minutes=rule.window_minutes))
            if event.ip_address: qs=qs.filter(ip_address=event.ip_address)
            if qs.count()>=rule.threshold:
                alert=SecurityAlert.objects.create(organization=event.organization,rule=rule,event=event,title=rule.name,details={"count":qs.count(),"condition":rule.condition},severity=rule.severity)
                created.append(alert)
                if rule.create_incident: IncidentService.create(event.organization,rule.name,"Alert rule threshold exceeded",event.event_type,"P1" if rule.severity=="CRITICAL" else "P2",event)
        return created

class ComplianceService:
    @staticmethod
    def control_score(control):
        return {"COMPLIANT":100,"PARTIAL":60,"IN_REVIEW":40,"NOT_STARTED":0,"NON_COMPLIANT":-100}.get(control.status,0)
    @classmethod
    def framework_score(cls,organization,framework):
        controls=list(ComplianceControl.objects.filter(organization=organization,framework=framework));
        if not controls:return 0
        return round(sum(cls.control_score(c) for c in controls)/len(controls),2)
    @classmethod
    def overdue_controls(cls,organization): return ComplianceControl.objects.filter(organization=organization,next_review_at__lt=timezone.now()).exclude(status="COMPLIANT")

class RiskAssessmentService:
    @staticmethod
    def residual(inherent,control): return max(0,min(100,float(inherent)*(1-float(control)/100)))
    @classmethod
    def assess(cls,organization,name,inherent,control,assessor=None,methodology="weighted"):
        residual=cls.residual(inherent,control)
        return SecurityRiskAssessment.objects.create(organization=organization,name=name,inherent_score=inherent,control_score=control,residual_score=residual,assessor=assessor,methodology=methodology,assessed_at=timezone.now(),status="COMPLETED")

class RetentionService:
    @classmethod
    def archive_expired(cls,organization=None):
        policies=AuditRetentionPolicy.objects.filter(is_active=True)
        if organization: policies=policies.filter(organization=organization)
        total=0
        for p in policies:
            cutoff=timezone.now()-timedelta(days=p.retention_days); qs=AuditEntry.objects.filter(organization=p.organization,created_at__lt=cutoff)
            if p.event_type: qs=qs.filter(model_label=p.event_type)
            rows=list(qs.values());
            if not rows: continue
            payload=json.loads(json.dumps(rows,default=str)); raw=json.dumps(payload,sort_keys=True).encode(); checksum=hashlib.sha256(raw).hexdigest()
            AuditArchive.objects.create(organization=p.organization,source_model="security.AuditEntry",source_count=len(rows),period_start=min(x["created_at"] for x in rows),period_end=max(x["created_at"] for x in rows),checksum=checksum,payload=payload)
            if p.archive_before_delete: qs.delete(); total+=len(rows)
        return total
