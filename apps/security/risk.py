"""Security risk analytics and scoring primitives used by dashboards and automation."""
from collections import Counter,defaultdict
from datetime import timedelta
from statistics import mean
from django.db.models import Avg,Count
from django.utils import timezone
from .models import SecurityEvent,SecurityIncident,SecurityAlert,UserSession,ComplianceControl

class RiskWeights:
    severity={"INFO":0,"LOW":8,"MEDIUM":25,"HIGH":55,"CRITICAL":90}
    outcome={"SUCCESS":0,"CHALLENGED":8,"FAILURE":18,"BLOCKED":12}
    event={"LOGIN_FAILURE":15,"PASSWORD_RESET":10,"PRIVILEGE_CHANGE":35,"EXPORT":20,"MFA_FAILURE":25,"SESSION_REVOKED":5,"ACCESS_DENIED":18}

class EventRiskScorer:
    def score(self,event):
        score=RiskWeights.severity.get(event.severity,0)+RiskWeights.outcome.get(event.outcome,0)+RiskWeights.event.get(event.event_type,0)
        metadata=event.metadata or {}
        if metadata.get("new_country"): score+=15
        if metadata.get("new_device"): score+=10
        if metadata.get("bulk_operation"): score+=12
        if metadata.get("admin_action"): score+=20
        return min(score,100)
    def classify(self,score):
        if score>=80:return "CRITICAL"
        if score>=60:return "HIGH"
        if score>=30:return "MEDIUM"
        if score>=10:return "LOW"
        return "INFO"
    def explain(self,event):
        factors=[]; base=RiskWeights.severity.get(event.severity,0); factors.append(("severity",base))
        outcome=RiskWeights.outcome.get(event.outcome,0)
        if outcome:factors.append(("outcome",outcome))
        event_weight=RiskWeights.event.get(event.event_type,0)
        if event_weight:factors.append(("event_type",event_weight))
        for key,weight in (("new_country",15),("new_device",10),("bulk_operation",12),("admin_action",20)):
            if (event.metadata or {}).get(key): factors.append((key,weight))
        return {"score":min(sum(v for _,v in factors),100),"factors":factors}

class SecurityTrendAnalyzer:
    def __init__(self,organization): self.organization=organization
    def events(self,days=30):
        start=timezone.now()-timedelta(days=days); return SecurityEvent.objects.filter(organization=self.organization,occurred_at__gte=start)
    def daily_counts(self,days=30):
        counts=defaultdict(int); qs=self.events(days).values_list("occurred_at","severity")
        for dt,severity in qs: counts[(dt.date().isoformat(),severity)]+=1
        return [{"date":d,"severity":s,"count":n} for (d,s),n in sorted(counts.items())]
    def severity_distribution(self,days=30): return dict(Counter(self.events(days).values_list("severity",flat=True)))
    def outcome_distribution(self,days=30): return dict(Counter(self.events(days).values_list("outcome",flat=True)))
    def top_event_types(self,days=30,limit=10): return list(self.events(days).values("event_type").annotate(total=Count("id")).order_by("-total")[:limit])
    def risk_average(self,days=30): return round(self.events(days).aggregate(avg=Avg("risk_score"))["avg"] or 0,2)
    def failure_rate(self,days=30):
        total=self.events(days).count(); failures=self.events(days).filter(outcome__in=["FAILURE","BLOCKED"]).count(); return round(failures/total*100,2) if total else 0
    def incident_rate(self,days=30):
        total=self.events(days).count(); incidents=SecurityIncident.objects.filter(organization=self.organization,created_at__gte=timezone.now()-timedelta(days=days)).count(); return round(incidents/total*100,2) if total else 0
    def executive_summary(self,days=30):
        return {"period_days":days,"events":self.events(days).count(),"severity":self.severity_distribution(days),"outcomes":self.outcome_distribution(days),"average_risk":self.risk_average(days),"failure_rate":self.failure_rate(days),"incident_rate":self.incident_rate(days),"top_events":self.top_event_types(days)}

class SessionRiskAnalyzer:
    def __init__(self,user): self.user=user
    def active(self): return UserSession.objects.filter(user=self.user,status="ACTIVE")
    def stale(self,minutes=60): return self.active().filter(last_seen_at__lt=timezone.now()-timedelta(minutes=minutes))
    def ip_distribution(self): return dict(Counter(self.active().values_list("ip_address",flat=True)))
    def device_distribution(self): return dict(Counter(self.active().values_list("device_fingerprint",flat=True)))
    def risk_flags(self):
        flags=[]
        if self.active().count()>5: flags.append("many_active_sessions")
        if self.stale().exists(): flags.append("stale_active_session")
        if len(self.ip_distribution())>3: flags.append("multiple_source_ips")
        if len(self.device_distribution())>3: flags.append("multiple_devices")
        return flags

class ComplianceRiskAnalyzer:
    def __init__(self,organization): self.organization=organization
    def control_status(self): return dict(Counter(ComplianceControl.objects.filter(organization=self.organization).values_list("status",flat=True)))
    def evidence_expiry(self,days=30): return ComplianceControl.objects.filter(organization=self.organization,evidence__expires_at__lte=timezone.now()+timedelta(days=days)).distinct().count()
    def gap_count(self): return ComplianceControl.objects.filter(organization=self.organization).exclude(status="COMPLIANT").count()
    def score(self):
        weights={"COMPLIANT":100,"PARTIAL":60,"IN_REVIEW":40,"NOT_STARTED":0,"NON_COMPLIANT":0}; statuses=list(ComplianceControl.objects.filter(organization=self.organization).values_list("status",flat=True)); return round(mean(weights.get(s,0) for s in statuses),2) if statuses else 0
