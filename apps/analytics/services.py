from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from time import perf_counter
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone
from .models import *

class AnalyticsEngine:
    """Application-level analytics engine with reusable aggregation primitives."""
    AGGREGATORS={'sum':Sum,'avg':Avg,'average':Avg,'count':Count}
    @staticmethod
    def aggregate(queryset, field, operation='sum', filters=None):
        if filters: queryset=queryset.filter(**filters)
        operation=operation.lower(); fn=AnalyticsEngine.AGGREGATORS.get(operation)
        if not fn: raise ValueError(f'Unsupported aggregation: {operation}')
        key=f'value'; result=queryset.aggregate(**{key:fn(field)})[key]
        return Decimal(str(result or 0)) if operation!='count' else int(result or 0)
    @staticmethod
    def percentage(part, whole):
        return (Decimal(str(part))/Decimal(str(whole))*Decimal('100')).quantize(Decimal('0.01')) if whole else Decimal('0')
    @staticmethod
    def moving_average(values, window=3):
        values=[Decimal(str(v)) for v in values]; output=[]
        for index in range(len(values)):
            sample=values[max(0,index-window+1):index+1]; output.append(sum(sample,Decimal('0'))/Decimal(len(sample)))
        return output
    @staticmethod
    def trend(values):
        if len(values)<2:return {'direction':'flat','change':Decimal('0'),'change_percent':Decimal('0')}
        first,last=Decimal(str(values[0])),Decimal(str(values[-1])); change=last-first
        return {'direction':'up' if change>0 else 'down' if change<0 else 'flat','change':change,'change_percent':AnalyticsEngine.percentage(change,abs(first))}

class MetricService:
    @staticmethod
    def record_snapshot(metric, value, captured_for=None, dimensions=None, metadata=None):
        captured_for=captured_for or timezone.now(); return AnalyticsSnapshot.objects.update_or_create(metric=metric,captured_for=captured_for,defaults={'organization':metric.organization,'value':Decimal(str(value)),'dimensions':dimensions or {},'metadata':metadata or {}})[0]
    @staticmethod
    def history(metric, days=30):
        since=timezone.now()-timedelta(days=days)
        return list(metric.snapshots.filter(captured_for__gte=since).order_by('captured_for').values('captured_for','value','dimensions'))
    @staticmethod
    def evaluate_kpi(kpi, value):
        value=Decimal(str(value)); target=Decimal(str(kpi.target)); status='on_target'
        if kpi.critical_threshold is not None and value<=kpi.critical_threshold: status='critical'
        elif kpi.warning_threshold is not None and value<=kpi.warning_threshold: status='warning'
        return {'value':value,'target':target,'variance':value-target,'status':status}

class DashboardService:
    @staticmethod
    def summary(dashboard):
        widgets=[]
        for widget in dashboard.widgets.select_related('metric'):
            item={'id':str(widget.id),'title':widget.title,'type':widget.widget_type,'configuration':widget.configuration,'position':widget.position}
            if widget.metric:item['metric']=widget.metric.code
            widgets.append(item)
        return {'dashboard':dashboard.name,'widgets':widgets,'filter_count':len(dashboard.filters or {})}
    @staticmethod
    def clone(dashboard, name, owner=None):
        clone=Dashboard.objects.create(organization=dashboard.organization,name=name,slug=f'{dashboard.slug}-copy-{timezone.now():%H%M%S}',description=dashboard.description,is_shared=False,layout=dashboard.layout.copy(),filters=dashboard.filters.copy(),owner=owner or dashboard.owner)
        for w in dashboard.widgets.all(): DashboardWidget.objects.create(dashboard=clone,title=w.title,widget_type=w.widget_type,metric=w.metric,configuration=w.configuration.copy(),position=w.position.copy(),refresh_seconds=w.refresh_seconds,is_visible=w.is_visible)
        return clone

class ReportService:
    @staticmethod
    def run(report, user=None, parameters=None):
        started=perf_counter(); run=ReportRun.objects.create(report=report,requested_by=user,parameters=parameters or {},status='running')
        try:
            result=ReportService.build_preview(report, parameters or {}); elapsed=int((perf_counter()-started)*1000)
            run.row_count=len(result['rows']); run.duration_ms=elapsed; run.result_snapshot=result; run.status='completed'; run.completed_at=timezone.now(); run.save(update_fields=['row_count','duration_ms','result_snapshot','status','completed_at'])
            return run
        except Exception as exc:
            run.status='failed'; run.error_message=str(exc); run.completed_at=timezone.now(); run.save(update_fields=['status','error_message','completed_at']); raise
    @staticmethod
    def build_preview(report, parameters=None):
        """Return a deterministic metadata preview; domain adapters can supply real rows."""
        return {'columns':report.columns or [],'rows':[],'source':report.source,'filters':report.filters or {},'parameters':parameters or {}}
    @staticmethod
    def history(report, limit=20): return report.runs.select_related('requested_by')[:limit]

class DomainAnalytics:
    @staticmethod
    def organization(organization):
        from apps.crm.models import Account
        from apps.projects.models import Project, ProjectStatus
        from apps.support.models import SupportTicket
        data={'accounts':Account.objects.filter(organization=organization).count(),'projects':Project.objects.filter(organization=organization).count(),'active_projects':Project.objects.filter(organization=organization,status=ProjectStatus.ACTIVE).count(),'support_tickets':SupportTicket.objects.filter(organization=organization).count()}
        data['project_completion_rate']=AnalyticsEngine.percentage(data['active_projects'],data['projects']); return data
    @staticmethod
    def sales(organization):
        try:
            from apps.sales.models import SalesOrder
            qs=SalesOrder.objects.filter(organization=organization); return {'orders':qs.count(),'total':AnalyticsEngine.aggregate(qs,'total_amount','sum')}
        except Exception:return {'orders':0,'total':Decimal('0')}
    @staticmethod
    def inventory(organization):
        try:
            from apps.inventory.models import Product
            return {'products':Product.objects.filter(organization=organization).count()}
        except Exception:return {'products':0}
    @staticmethod
    def support(organization):
        from apps.support.models import SupportTicket, TicketStatus
        qs=SupportTicket.objects.filter(organization=organization); total=qs.count(); closed=qs.filter(status__in=[TicketStatus.RESOLVED,TicketStatus.CLOSED]).count(); return {'total':total,'closed':closed,'resolution_rate':AnalyticsEngine.percentage(closed,total)}
