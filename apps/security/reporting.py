"""Operational security reports with stable dictionary output for UI/export jobs."""
from datetime import timedelta
from django.db.models import Count,Avg
from django.utils import timezone
from .models import *
from .risk import SecurityTrendAnalyzer,ComplianceRiskAnalyzer

class SecurityReportBuilder:
    def __init__(self,organization): self.organization=organization
    def event_report(self,days=30):
        qs=SecurityEvent.objects.filter(organization=self.organization,occurred_at__gte=timezone.now()-timedelta(days=days))
        rows=qs.values("event_type","severity","outcome").annotate(total=Count("id"),avg_risk=Avg("risk_score")).order_by("-total")
        return {"name":"Security Event Report","period_days":days,"rows":list(rows)}
    def alert_report(self,days=30):
        qs=SecurityAlert.objects.filter(organization=self.organization,created_at__gte=timezone.now()-timedelta(days=days)); return {"total":qs.count(),"open":qs.filter(status="OPEN").count(),"critical":qs.filter(severity="CRITICAL").count(),"rows":list(qs.values("title","severity","status","created_at"))}
    def incident_report(self,days=90):
        qs=SecurityIncident.objects.filter(organization=self.organization,created_at__gte=timezone.now()-timedelta(days=days)); return {"total":qs.count(),"open":qs.exclude(status__in=["RESOLVED","CLOSED"]).count(),"by_priority":list(qs.values("priority").annotate(total=Count("id"))),"by_category":list(qs.values("category").annotate(total=Count("id")))}
    def access_review_report(self):
        reviews=AccessReview.objects.filter(organization=self.organization); return {"total":reviews.count(),"open":reviews.filter(status__in=["OPEN","IN_PROGRESS"]).count(),"completed":reviews.filter(status="COMPLETED").count(),"items":list(AccessReviewItem.objects.filter(review__organization=self.organization).values("decision").annotate(total=Count("id")))}
    def compliance_report(self): return {"control_status":ComplianceRiskAnalyzer(self.organization).control_status(),"score":ComplianceRiskAnalyzer(self.organization).score(),"gaps":ComplianceRiskAnalyzer(self.organization).gap_count(),"expiring_evidence":ComplianceRiskAnalyzer(self.organization).evidence_expiry()}
    def executive_report(self):
        trends=SecurityTrendAnalyzer(self.organization); return {"security_events":trends.executive_summary(),"incidents":self.incident_report(),"alerts":self.alert_report(),"access_reviews":self.access_review_report(),"compliance":self.compliance_report()}

class ExportFormatter:
    @staticmethod
    def csv_rows(report):
        rows=[]
        for key,value in report.items():
            if isinstance(value,list): rows.extend(value)
            elif isinstance(value,dict): rows.append({"section":key,"value":value})
            else: rows.append({"section":key,"value":value})
        return rows
    @staticmethod
    def flatten(data,prefix=""):
        result={}
        if isinstance(data,dict):
            for key,value in data.items(): result.update(ExportFormatter.flatten(value,f"{prefix}.{key}" if prefix else key))
        elif isinstance(data,list): result[prefix]="; ".join(str(x) for x in data)
        else: result[prefix]=data
        return result
